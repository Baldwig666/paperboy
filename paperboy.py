from flask import Flask, render_template_string, request, redirect, send_from_directory, session
from PIL import Image, ImageOps
import os
import sys
import subprocess
import os
import json

from config import SECRET_KEY, CATEGORY_PASSWORD

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Waveshare driver
libdir = os.path.join(BASE_DIR, 'lib')
if os.path.exists(libdir): sys.path.append(libdir)
try:
    import epd13in3E
    epd = epd13in3E.EPD()
except:
    print ("ERROR! unable to load waveshare driver!")


EPD_WORKING = False

app = Flask(__name__)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
THUMB_FOLDER = os.path.join(BASE_DIR, "uploads/thumbs")
TEMP_FOLDER = os.path.join(BASE_DIR, "temp")
CATEGORY_FILE = os.path.join(BASE_DIR, "categories.json")
VAULT_FILE = os.path.join(BASE_DIR, "vault.json")
CURRENT_IMAGE = os.path.join(BASE_DIR, "current.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

SPECTRA6_PHOTO = [
    (28, 32, 36),
    (235, 235, 232),
    (225, 210, 120),
    (150, 45, 45),
    (40, 90, 160),
    (40, 105, 70),
]

SPECTRA6_COMIC = [
    (20, 20, 20),
    (235, 235, 235),
    (240, 220, 70),
    (180, 20, 30),
    (30, 80, 170),
    (20, 100, 40),
]


SPECTRA6_REAL_WORD_RGB = [
    (25, 30, 33),
    (232, 232, 232),
    (239, 222, 68),
    (178, 19, 24),
    (33, 87, 186),
    (18, 95, 32),
]


SPECTRA6_RGB = [
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

def get_current():
    if not os.path.exists(VAULT_FILE):
        return {}
    with open(CURRENT_IMAGE, "r") as f:
        return json.load(f)

def set_current(loaded_image):
    with open(CURRENT_IMAGE, "w") as f:
        json.dump(loaded_image, f, indent=4)

def image_scale(path):
    image = Image.open(path)
    img_width, img_height = image.size

    epaper_width = epd.width
    epaper_height = epd.height

    # if landscape image is detected the image will be rotated according to 
    # the given orientation to be portrait native and splayed correctly
    if ((img_width / img_height) > 1 ):
        if LANDSCAPE_ORIENTATION == "left":
            image = image.rotate(90)
            img_width, img_height = image.size
        else: 
            image = image.rotate(270)
            img_width, img_height = image.size

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

    if sel_palette == "photo":
        palette = (
            tuple(v for rgb in SPECTRA6_PHOTO for v in rgb)
            + SPECTRA6_REAL_WORD_RGB[0] * 250
        )
    elif sel_palette == "comic":
        palette = (
            tuple(v for rgb in SPECTRA6_COMIC for v in rgb)
            + SPECTRA6_REAL_WORD_RGB[0] * 250
        )
    elif sel_palette == "spectra6":
        palette = (
            tuple(v for rgb in SPECTRA6_REAL_WORD_RGB for v in rgb)
            + SPECTRA6_REAL_WORD_RGB[0] * 250
        )
    else:
        palette = (
            tuple(v for rgb in SPECTRA6_RGB for v in rgb)
            + SPECTRA6_REAL_WORD_RGB[0] * 250
        )

    pal_image.putpalette(palette)
    img = Image.open(path).quantize(dither=Image.Dither.FLOYDSTEINBERG, palette=pal_image)

    # Build a new device palette
    device_palette = (
        tuple(v for rgb in SPECTRA6_RGB for v in rgb)
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
  height: 400px;
  margin-bottom: 24px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}

.card-gallery {
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
 justify-content: center;
 gap: 12px;
}

.btn-std {
 display: flex;
 gap: 12px;
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

  <table style="width:100%">
  <tr style="width100%">
  <td>

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
      </label><br>

      <label>
        <input type="radio" name="palette" value="photo">
        Spectra 6 photo palette
      </label><br>

      <label>
        <input type="radio" name="palette" value="comic">
        Spectra 6 comic palette
      </label><br><br>


      <button class="btn-primary" type="submit">Upload image</button>
    </form>
  </div>

  </td>

  <td>
  <div class="card">
  <div class="item">
    <img class="thumb" src="/thumb/{{image_on_paper}}">
  </div>
  </div>

  </td>
  <td>

  <div class="card">
      <form action="/clear" method="post">
        <button class="btn-danger" type="submit">Clear Display</button>
      </form>

      <br>

      <form action="/shutdown" method="post"
            onsubmit="return confirm('Really shut down the Raspberry Pi?');">
        <button class="btn-danger" type="submit">Shutdown Raspberry Pi</button>
      </form>
  </div>

  </td>
  </tr>
  </table>

  <div class="card-gallery">
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

        {% if not session.get("unlocked") %}
        <form method="post" action="/unlock">
          <input type="password" name="password" placeholder="Unlock password">
          <button class="btn-primary" type="submit">Unlock</button>
        </form>
        {% endif %}


        {% if session.get("unlocked") %}
        <form method="post" action="/lock">
          <button class="btn-muted" type="submit">Lock categories </button>
        </form>
        {% endif %}

      {% if session.get("unlocked") %}
      <br>
      <div class="btn-std">
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
        <br>
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

    image_on_paper = ''.join(get_current())

    images = [
        f for f in os.listdir(UPLOAD_FOLDER)
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))
    ]

    all_cats = get_all_categories(categories)

    def image_category(img):
        return categories.get(img, "default")

    # Hide protected categories unless unlocked
    if not session.get("unlocked"):
        if image_category(image_on_paper) in PROTECTED_CATEGORIES:
            image_on_paper = "login_blurr.png"

        all_cats = [c for c in all_cats if c not in PROTECTED_CATEGORIES]
        if selected_category in PROTECTED_CATEGORIES:
            selected_category = "default"

    images.sort()

    filtered = [
        img for img in images
        if image_category(img) == selected_category
    ]

    return render_template_string(
        HTML,
        filtered=filtered,
        categories=categories,
        all_cats=all_cats,
        selected_category=selected_category,
        image_on_paper=image_on_paper
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
    img = Image.open(tmp_path)
    img = ImageOps.exif_transpose(img)
    img.save(bmp_path, "BMP")
    image_scale(bmp_path)
    make_thumbnail(tmp_path)
    convert_for_spectra6(bmp_path, dither_method)
    os.remove(tmp_path)
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
        set_current(name)
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
