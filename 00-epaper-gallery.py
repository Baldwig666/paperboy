from flask import Flask, render_template_string, request, redirect, send_from_directory
from PIL import Image
import os

# Waveshare driver
import epd13in3E
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "/bin/waveshare13x3epaper/uploads"
THUMB_FOLDER = "/bin/waveshare13x3epaper/uploads/thumbs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

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

<h3>Image Gallery</h3>
<div class="gallery">
{% for f in files %}
  <div class="item">
    <a href="/show/{{f}}">
      <img class="thumb" src="/thumb/{{f}}">
    </a>
    <form action="/delete/{{f}}" method="post">
      <button class="delbtn" type="submit">Delete</button>
    </form>
  </div>
{% endfor %}
</div>

</body>
</html>
"""

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

@app.route("/")
def index():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f != "thumbs"]
    return render_template_string(HTML, files=files)

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

    img = convert_for_spectra6(path)

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

@app.route("/clear", methods=["POST"])
def clear():
    epd = get_epd()
    epd.Clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
