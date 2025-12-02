from flask import Flask, render_template_string, request, redirect, send_from_directory
from PIL import Image
import os

# Waveshare driver
import epd13in3E
import subprocess
import os
import json

app = Flask(__name__)

UPLOAD_FOLDER = "/usr/locl/bin/paperboy/uploads"
THUMB_FOLDER = "/usr/locl/bin/paperboy/uploads/thumbs"
CATEGORY_FILE = "/usr/locl/bin/paperboy/categories.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)


def load_categories():
    if not os.path.exists(CATEGORY_FILE):
        return {}
    with open(CATEGORY_FILE, "r") as f:
        return json.load(f)

def save_categories(cats):
    with open(CATEGORY_FILE, "w") as f:
        json.dump(cats, f, indent=4)

def get_all_categories(catmap):
    cats = set(catmap.values())
    cats.add("default")
    return sorted(list(cats))

def get_epd():
    epd = epd13in3E.EPD()
    epd.Init()
    return epd

def convert_for_spectra6(path):

    epd = epd13in3E.EPD()
    img = Image.open(path).convert("RGB")
    img = img.resize((epd.width, epd.height))
    return img

def make_thumbnail(path, filename):
    thumb_path = os.path.join(THUMB_FOLDER, filename)
    img = Image.open(path)
    img.thumbnail((150, 150))
    img.save(thumb_path)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>E-Paper Frame</title>
<style>
body { font-family: Arial; margin: 40px; max-width: 900px; }
button { padding: 8px 16px; margin: 5px 0; cursor: pointer; }
.thumb {
    width: 150px;
    border: 2px solid #ccc;
    margin: 5px;
}
.thumb:hover { border-color: #000; }
.gallery { display: flex; flex-wrap: wrap; }
.item { margin: 10px; text-align: center; }
.delbtn {
    background: #d9534f;
    color: white;
    border: none;
    padding: 5px 10px;
    margin-top: 5px;
}
</style>
</head>
<body>
<h2>E-Paper Picture Frame</h2>

<form action="/upload" method="post" enctype="multipart/form-data">
  <input type="file" name="file" required>
  <button type="submit">Upload image</button>
</form>

<form action="/uploadad" method="post" enctype="multipart/form-data">
  <input type="file" name="file" required>
  <button type="submit">Upload & Display image</button>
</form>

<form action="/clear" method="post">
  <button type="submit" style="background: #d9534f; color: white;">Clear Display</button>
</form>

<form action="/shutdown" method="post" onsubmit="return confirm('Really shut down the Raspberry Pi?');">
    <button type="submit" style="background:red;color:white;padding:10px;border:none;border-radius:5px;">
        Shutdown Raspberry Pi
    </button>
</form>

<hr>

<h2>Gallery</h2>

<form method="post" action="/add_category">
    <input type="text" name="new_category" placeholder="New category name">
    <button type="submit">Create category</button>
</form>

<form method="get" action="/" style="display:inline-block;">
    <label>Select category: </label>
    <select name="cat" onchange="this.form.submit()">
        {% for c in all_cats %}
        <option value="{{c}}" {% if c == selected_category %}selected{% endif %}>{{c}}</option>
        {% endfor %}
    </select>
</form>
<form action="/delete/{{f}}" method="post">
    <button class="delbtn" type="submit">Delete</button>
</form>
<!-- Delete Category Button -->
{% if selected_category != "default" %}
<form method="post" action="/delete_category" style="display:inline-block; margin-left:10px;">
    <input type="hidden" name="category" value="{{selected_category}}">
    <button type="submit" onclick="return confirm('Delete category {{selected_category}}? All images will move to default.')">
        Delete Category
    </button>
</form>
{% endif %}

<hr>

<div class="gallery">
{% for img in filtered %}
<div class="item">

    <a href="/show/{{img}}">
      <img class="thumb" src="/thumb/{{img}}">
    </a>

    <form method="post" action="/set_category">
        <input type="hidden" name="image" value="{{img}}">
        <select name="category" onchange="this.form.submit()">
            {% for c in all_cats %}
            <option value="{{c}}" {% if categories.get(img,'default') == c %}selected{% endif %}>{{c}}</option>
            {% endfor %}
        </select>
    </form>
</div>
{% endfor %}
</div>

</body>
</html>
"""


@app.route("/")
def index():
    selected_category = request.args.get("cat", "default")
    categories = load_categories()

    # all image filenames (no thumbnails)
    images = [f for f in os.listdir(UPLOAD_FOLDER) if not f.endswith("thumbs")]

    # full list of categories
    all_cats = get_all_categories(categories)

    # filter images by selected category
    def image_category(img):
        return categories.get(img, "default")

    filtered = [img for img in images if image_category(img) == selected_category]


    return render_template_string(HTML,
        filtered=filtered,
        categories=categories,
        all_cats=all_cats,
        selected_category=selected_category
    )

@app.route("/thumb/<name>")
def thumb(name):
    return send_from_directory(THUMB_FOLDER, name)

@app.route("/shutdown", methods=["POST"])
def shutdown():
    # Shut down the system
    subprocess.call(["sudo", "shutdown", "-h", "now"])
    return "Shutting down..."

@app.route("/uploadad", methods=["POST"])
def uploadad():
    f = request.files["file"]
    filename = f.filename
    path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(path)

    make_thumbnail(path, filename)

    img = convert_for_spectra6(path)
    epd = get_epd()
    epd.Init()
    epd.Clear()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    filename = f.filename
    path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(path)

    make_thumbnail(path, filename)

#    img = convert_for_spectra6(path)

    return redirect("/")

@app.route("/show/<name>")
def show(name):

    path = os.path.join(UPLOAD_FOLDER, name)
    img = convert_for_spectra6(path)
    epd = get_epd()
    epd.Init()
    epd.Clear()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    return redirect("/")

@app.route("/delete/<name>", methods=["POST"])
def delete(name):
    img_path = os.path.join(UPLOAD_FOLDER, name)
    thumb_path = os.path.join(THUMB_FOLDER, name)

    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    return redirect("/")

@app.route("/set_category", methods=["POST"])
def set_category():
    image = request.form["image"]
    category = request.form["category"]

    categories = load_categories()

    # Default category means removing from JSON
    if category == "default":
        if image in categories:
            del categories[image]
    else:
        categories[image] = category

    save_categories(categories)
    return redirect("/")

@app.route("/add_category", methods=["POST"])
def add_category():
    newcat = request.form["new_category"].strip()
    if newcat:
        cats = load_categories()
        with open('/proc/uptime', 'r') as f:
           uptime_seconds = float(f.readline().split()[0])
        cats[uptime_seconds] = newcat
        save_categories(cats)
    return redirect("/")


@app.route("/delete_category", methods=["POST"])
def delete_category():
    cat_to_delete = request.form["category"]

    # Never delete default
    if cat_to_delete == "default":
        return redirect("/")

    categories = load_categories()

    # Remove category from all images using it
    new_categories = {}
    for img, cat in categories.items():
        if cat != cat_to_delete:
            new_categories[img] = cat

    save_categories(new_categories)

    return redirect("/")

@app.route("/clear", methods=["POST"])
def clear():
    epd = get_epd()
    epd.Clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
