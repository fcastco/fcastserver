# Python packages
import os

# 3rd party packages
from sanic.response import redirect
from sanic import Blueprint
import aiofiles
from uuid import uuid4

file_bp = Blueprint('file_bp')

ALLOWED_FILE_EXTENSIONS = ["pdf", "csv"]
ALLOWED_FILE_TYPES = ["application/pdf", "text/csv"]

async def write_file(path, body):
    async with aiofiles.open(path, 'wb') as f:
        await f.write(body)
    f.close()


def valid_file_type(file_name, file_type):
    file_name_type = file_name.split('.')[-1].lower()
    if file_name_type in ALLOWED_FILE_EXTENSIONS and\
            file_type in ALLOWED_FILE_TYPES:
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


def add_file_to_session(filename, request):
    try:
        request['session']['filenames']
    except KeyError:
        request['session']['filenames'] = {}
    file_uuid = str(uuid4())
    request['session']['filenames'].update({file_uuid: filename})
    return


@file_bp.route("file/zip", methods=["POST"])
def create_zip(request):
    user_id = request.form.get("user_id")
    pw = request.form.get("zip_password")
    download_dir = request.app.config.DOWNLOAD_DIR
    # Create upload folder if doesn't exist
    if not os.path.exists(download_dir):
        os.makedirs(upload_dir)
    upload_dir = request.app.config.UPLOAD_DIR + "/" + user_id
    import subprocess
    subprocess.call(['zip', '-j', '-r', '-P'+pw, download_dir + "/" + user_id + '.zip', upload_dir])
    return redirect("/d/"+user_id+".zip")


@file_bp.route("file/delete", methods=["POST"])
def rm_file_from_session(request):
    upload_dir = request.app.config.UPLOAD_DIR
    user_id = request.form.get("user_id")
    file_uuid = request.form.get("file_uuid")
    print(request.form)
    filename = request['session']['filenames'][file_uuid]
    file_path = upload_dir + "/" + user_id + "/" + filename
    if os.path.exists(file_path):
        os.remove(file_path)
    del request['session']['filenames'][file_uuid]
    return redirect('/?deleted_file')


@file_bp.route("/upload", methods=["POST"])
async def process_upload(request):

    upload_dir = request.app.config.UPLOAD_DIR
    # Create upload folder if doesn't exist
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    user_id = request['session']['user_id']
    user_dir = upload_dir + "/" + user_id
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

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
        file_path = f"{user_dir}/{filename}"
        add_file_to_session(filename, request)
        await write_file(file_path, upload_file.body)
        return redirect('/?error=none')
