from flask import Flask, render_template_string, request, redirect, send_from_directory, session
from PIL import Image, ImageOps
import os

# Waveshare driver
import epd13in3E
import subprocess
import os
import json

app = Flask(__name__)

app.secret_key = "erjbh4r347rb3r28t6r2rsdc"

UPLOAD_FOLDER = "/usr/local/bin/paperboy/uploads"
THUMB_FOLDER = "/usr/local/bin/paperboy/uploads/thumbs"
TEMP_FOLDER = "/usr/local/bin/paperboy/temp"
CATEGORY_FILE = "/usr/local/bin/paperboy/categories.json"
VAULT_FILE = "/usr/local/bin/paperboy/vault.json"
SECRET_FILE = "/usr/local/bin/paperboy/secret"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

with open(SECRET_FILE) as file:
    CATEGORY_PASSWORD = ''.join(file.read().splitlines())

EPD_WORKING = False

epd = epd13in3E.EPD()

SPECTRA6_REAL_WORD_RGB = [
    (25, 30, 33),
    (232, 232, 232),
    (239, 222, 68),
    (178, 19, 24),
    (33, 87, 186),
    (18, 95, 32),
]

SPECTRA6_DEVICE_RGB = [
    (0, 0, 0),  # BLACK
    (255, 255, 255),  # WHITE
    (255, 255, 0),  # YELLOW
    (255, 0, 0),  # RED
    (0, 0, 255),  # BLUE
    (0, 255, 0),  # GREEN
]

def load_categories():
    if not os.path.exists(CATEGORY_FILE):
        return {}
    with open(CATEGORY_FILE, "r") as f:
        return json.load(f)

def save_categories(cats):
    with open(CATEGORY_FILE, "w") as f:
        json.dump(cats, f, indent=4)

def load_vault():
    if not os.path.exists(VAULT_FILE):
        return {}
    with open(VAULT_FILE, "r") as f:
        return json.load(f)

def save_vault(cats):
    with open(VAULT_FILE, "w") as f:
        json.dump(cats, f, indent=4)

def get_all_categories(catmap):
    cats = set(catmap.values())
    cats.add("default")
    return sorted(list(cats))

def image_scale(path):
    image = Image.open(path)
    img_width, img_height = image.size

    epaper_width = epd.width
    epaper_height = epd.height

    # Computed scaling
    scale_ratio = max(epaper_width / img_width, epaper_height / img_height)

    # Calculate the size after scaling
    resized_width = int(img_width * scale_ratio)
    resized_height = int(img_height * scale_ratio)

    # Resize image
    output_image = image.resize((resized_width, resized_height), Image.LANCZOS)

    # Create the target image and center the resized image
    resized_image = Image.new('RGB', (epaper_width, epaper_height), (255, 255, 255))
    left = (epaper_width - resized_width) // 2
    top = (epaper_height - resized_height) // 2
    resized_image.paste(output_image, (left, top))

    resized_image.save(path, format="BMP")
    return resized_image


def convert_for_spectra6(path, sel_palette):

    pal_image = Image.new("P", (1,1))

    palette = (
        tuple(v for rgb in SPECTRA6_REAL_WORD_RGB for v in rgb)
        + SPECTRA6_REAL_WORD_RGB[0] * 250
    )
    
    pal_image.putpalette(palette)

    img = Image.open(path).quantize(dither=Image.Dither.FLOYDSTEINBERG, palette=pal_image)

    if sel_palette:
        # Build a new device palette
        device_palette = (
            tuple(v for rgb in SPECTRA6_DEVICE_RGB for v in rgb)
            + (0, 0, 0) * 250
        )
        img.putpalette(device_palette)

    img = img.convert("RGB")

    img.save(path)

    return img

def make_thumbnail(path):

    thumb_path = os.path.join(THUMB_FOLDER, os.path.basename(path).split('/')[-1])
    base, _ = os.path.splitext(thumb_path)
    bmp_path= base + ".bmp"
    img = Image.open(path)
    img.thumbnail((150, 150))
    img.save(bmp_path, "BMP" )


HTML = """

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>E-Paper Frame</title>

<style>
:root {
  --bg: #f4f6f8;
  --card: #ffffff;
  --border: #e0e0e0;
  --primary: #2563eb;
  --danger: #dc2626;
  --muted: #6b7280;
  --radius: 12px;
}

* {
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  margin: 0;
  padding: 40px;
  color: #111;
}

h2 {
  margin-top: 0;
}

.container {
  max-width: 1200px;
  margin: auto;
}

.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}

button {
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

button:hover {
  opacity: 0.9;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-muted {
  background: #e5e7eb;
}

input[type="file"],
input[type="text"],
input[type="password"],
select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

fieldset {
  border: none;
  padding: 0;
  margin: 0;
}

legend {
  font-weight: 600;
  margin-bottom: 10px;
}

.btn-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.item {
  background: #fafafa;
  border-radius: var(--radius);
  padding: 12px;
  text-align: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.item:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.08);
}

.thumb {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border);
  margin-bottom: 10px;
}

details summary {
  cursor: pointer;
  font-weight: 500;
  color: var(--primary);
}

hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 24px 0;
}

small {
  color: var(--muted);
}
</style>
</head>

<body>
<div class="container">

  <div class="card">
    <h2>E-Paper Picture Frame</h2>

    <form action="/upload" method="post" enctype="multipart/form-data">
      <legend>Upload image</legend>

      <input type="file" name="file" required accept=".bmp,.png,.jpg,.jpeg"><br><br>

      <label>
        <input type="radio" name="palette" value="default">
        Default palette
      </label><br>

      <label>
        <input type="radio" name="palette" value="spectra6" checked>
        Spectra 6 device palette
      </label><br><br>

      <button class="btn-primary" type="submit">Upload image</button>
    </form>
  </div>

  <div class="card">
    <div class="btn-row">
      <form action="/clear" method="post">
        <button class="btn-danger" type="submit">Clear Display</button>
      </form>

      <form action="/shutdown" method="post"
            onsubmit="return confirm('Really shut down the Raspberry Pi?');">
        <button class="btn-danger" type="submit">Shutdown Raspberry Pi</button>
      </form>
    </div>
  </div>

  <div class="card">
    <h2>Gallery</h2>

    <form method="get" action="/">
      <label>Category:</label>
      <select name="cat" onchange="this.form.submit()">
        {% for c in all_cats %}
        <option value="{{c}}" {% if c == selected_category %}selected{% endif %}>{{c}}</option>
        {% endfor %}
      </select>
    </form>

<br>

    <details>
      <summary>Settings</summary>
      <br>

      <form method="post" action="/add_category">
        <input type="text" name="new_category" placeholder="New category name">
        <button class="btn-primary" type="submit">Create</button>
      </form>

      <br>

      <div class="btn-row">
        <form method="post" action="/unlock">
          <input type="password" name="password" placeholder="Unlock password">
          <button class="btn-primary" type="submit">Unlock</button>
        </form>

        {% if session.get("unlocked") %}
        <form method="post" action="/lock">
          <button class="btn-muted" type="submit">Lock</button>
        </form>
        {% endif %}
      </div>

      {% if session.get("unlocked") %}
      <br>
      <div class="btn-row">
        <form method="post" action="/hide_category">
          <input type="hidden" name="hide" value="{{selected_category}}">
          <button class="btn-muted" type="submit">Hide Category</button>
        </form>

        <form method="post" action="/unhide_category">
          <input type="hidden" name="unhide" value="{{selected_category}}">
          <button class="btn-muted" type="submit">Unhide Category</button>
        </form>
        {% if selected_category != "default" %}
         <form method="post" action="/delete_category" >
          <input type="hidden" name="category" value="{{selected_category}}">
          <button class="btn-danger" type="submit"
           onclick="return confirm('Delete category {{selected_category}}?');">
           Delete Category
          </button>
         </form>
    {% endif %}

      </div>
      {% endif %}
    </details>

    <br>

    <hr>

    <div class="gallery">
      {% for img in filtered %}
      <div class="item">
        <a href="/view/{{img}}">
          <img class="thumb" src="/thumb/{{img}}">
        </a>

        <div class="btn-row">
          <a href="/show/{{img}}">
            <button class="btn-primary" type="button">Show</button>
          </a>

          <form action="/delete/{{img}}" method="post"
                onsubmit="return confirm('Really delete image?');">
            <button class="btn-danger" type="submit">Delete</button>
          </form>
        </div>

        <form method="post" action="/set_category">
          <input type="hidden" name="image" value="{{img}}">
          <select name="category" onchange="this.form.submit()">
            {% for c in all_cats %}
            <option value="{{c}}" {% if categories.get(img,'default') == c %}selected{% endif %}>
              {{c}}
            </option>
            {% endfor %}
          </select>
        </form>
      </div>
      {% endfor %}
    </div>
  </div>

</div>
</body>
</html>


"""


@app.route("/")
def index():
    selected_category = request.args.get("cat", "default")
    categories = load_categories()
    PROTECTED_CATEGORIES = load_vault()

    images = [
        f for f in os.listdir(UPLOAD_FOLDER)
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))
    ]

    all_cats = get_all_categories(categories)

    # Hide protected categories unless unlocked
    if not session.get("unlocked"):
        all_cats = [c for c in all_cats if c not in PROTECTED_CATEGORIES]
        if selected_category in PROTECTED_CATEGORIES:
            selected_category = "default"

    images.sort()

    def image_category(img):
        return categories.get(img, "default")

    filtered = [
        img for img in images
        if image_category(img) == selected_category
    ]

    return render_template_string(
        HTML,
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

@app.route("/upload", methods=["POST"])
def upload():

    f = request.files["file"]
    dither_method = request.form["palette"]
    filename = f.filename
    tmp_path = os.path.join(TEMP_FOLDER, filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    base, _ = os.path.splitext(path)    
    bmp_path= base + ".bmp"
    f.save(tmp_path)

    if dither_method == "spectra6":
        dpal_enabled = True
    else:
        dpal_enabled = False

    img = Image.open(tmp_path)
    img.save(bmp_path, "BMP")
    os.remove(tmp_path)
    image_scale(bmp_path)
    make_thumbnail(bmp_path)
    convert_for_spectra6(bmp_path, dpal_enabled)
    EPD_WORKING = False
    return redirect("/")

@app.route("/view/<name>")
def view(name):
    return send_from_directory(UPLOAD_FOLDER, name)

@app.route("/show/<name>")
def show(name):
    global EPD_WORKING
    print(EPD_WORKING)
    if EPD_WORKING:
        return "ePaper bussy.... please wait."
    else:
        EPD_WORKING = True
        path = os.path.join(UPLOAD_FOLDER, name)
        img = Image.open(path)
        epd.Init()
        epd.Clear()
        epd.display(epd.getbuffer(img))
        epd.sleep()
        EPD_WORKING = False
    return redirect(request.referrer or "/")

@app.route("/delete/<name>", methods=["POST"])
def delete(name):
    img_path = os.path.join(UPLOAD_FOLDER, name)
    thumb_path = os.path.join(THUMB_FOLDER, name)

    categories = load_categories()

    if name in categories:
        del categories[name]

    save_categories(categories)

    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(thumb_path):
        os.remove(thumb_path)

    return redirect(request.referrer or "/")

@app.route("/unlock", methods=["POST"])
def unlock():
    if request.form.get("password") == CATEGORY_PASSWORD:
        session["unlocked"] = True
        print("session unlocked")
    else:
        print("Session unlock failed. expected: ", CATEGORY_PASSWORD, " got: ", request.form.get("password"))
        print(type(CATEGORY_PASSWORD))
        print(type(request.form.get("password")))
    return redirect(request.referrer or "/")

@app.route("/lock", methods=["POST"])
def lock():
    session.pop("unlocked", None)
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
    return "", 204

@app.route("/add_category", methods=["POST"])
def add_category():
    newcat = request.form["new_category"].strip()
    if newcat:
        cats = load_categories()
        with open('/proc/uptime', 'r') as f:
           uptime_seconds = float(f.readline().split()[0])
        cats[uptime_seconds] = newcat
        save_categories(cats)
    return redirect(request.referrer or "/")

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

    return  redirect ("/?cat=default")

@app.route("/hide_category", methods=["POST"])
def hide_category():
    category = request.form["hide"].strip()
    if category:
        vault = load_vault()
        if category in vault:
            return redirect(request.referrer or "/")
        else: 
            vault.append(category)
        save_vault(vault)
    return "", 204

@app.route("/unhide_category", methods=["POST"])
def unhide_category():
    category = request.form["unhide"].strip()
    if category:
        vault = load_vault()
        if category in vault:
            vault.remove(category)
        else:
            return "", 204

        save_vault(vault)
    return redirect(request.referrer or "/")

@app.route("/clear", methods=["POST"])
def clear():
    epd.Clear()
    epd.sleep()
    return redirect(request.referrer or "/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
