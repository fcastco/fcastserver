#Python
import os
from datetime import datetime

# 3rd party packages
from sanic import Sanic
from sanic.response import json
from sanic.response import redirect
from sanic_jinja2 import SanicJinja2
import aiofiles

app = Sanic()
jinja = SanicJinja2(app)
app.config.from_envvar('MYAPP_SETTINGS')

async def write_file(path, body):
    async with aiofiles.open(path, 'wb') as f:
        await f.write(body)
    f.close()

def valid_file_type(file_name, file_type):
    file_name_type = file_name.split('.')[-1]
    if file_name_type == "pdf" and file_type == "application/pdf":
        return True
    return False

def valid_file_size(file_body):
    if len(file_body) < 10485760:
        return True
    return False

def secure_filename(filename):
    from unicodedata import normalize
    import re
    filename = normalize("NFKD", filename).encode("ascii", "ignore")
    filename = filename.decode("ascii")
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")
    _filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")
    filename = str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip(
        "._"
    )
    if (
        os.name == "nt"
        and filename
        and filename.split(".")[0].upper() in _windows_device_files
    ):
        filename = "_" + filename

    return filename


@app.route("/", methods=["GET"])
async def front_page(request):
    print(app.config.UPLOAD_DIR)
    return jinja.render("index.html", request)

@app.route("/upload", methods=["POST"])
async def process_upload(request):
    # Create upload folder if doesn't exist
    if not os.path.exists(app.config.UPLOAD_DIR):
        os.makedirs(app.config.UPLOAD_DIR)

    # Ensure a file was sent
    upload_file = request.files.get('file_names')
    if not upload_file:
        return redirect("/?error=no_file")

    # Clean up the filename in case it creates security risks
    filename = secure_filename(upload_file.name)

    # Ensure the file is a valid type and size, and if so
    # write the file to disk and redirect back to main
    if not valid_file_type(upload_file.name, upload_file.type):
        return redirect('/?error=invalid_file_type')
    elif not valid_file_size(upload_file.body):
        return redirect('/?error=invalid_file_size')
    else:
        file_path = f"{app.config.UPLOAD_DIR}/{str(datetime.now())}.pdf"
        await write_file(file_path, upload_file.body)
        return redirect('/?error=none')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
