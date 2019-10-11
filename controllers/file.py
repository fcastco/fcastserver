# Python packages
import os

# 3rd party packages
from sanic.response import redirect
from sanic.response import file_stream
from sanic_motor import BaseModel
from sanic import Blueprint
from sanic.response import text
import aiofiles
from uuid import uuid4
from pymongo import ReturnDocument

file_bp = Blueprint('file_bp')

ALLOWED_FILE_EXTENSIONS = ["pdf", "csv"]
ALLOWED_FILE_TYPES = ["application/pdf", "text/csv"]


class User(BaseModel):
    __coll__ = 'users'
    __unique_fields__ = ['user_id']


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
    return file_uuid


async def get_user(user_id):
    user = await User.find_one_and_update(
        {'user_id':user_id},
        {'$set':{'user_id':user_id}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return user
        

async def add_file_to_db(user, filename):
    filenames = user.get("filenames", {})
    file_uuid = str(uuid4())
    filenames.update({file_uuid: filename})
    user = await User.update_one({'user_id':user['user_id']}, {'$set':{'filenames':filenames}})
    return file_uuid


@file_bp.route("file/zip", methods=["POST", "OPTIONS"])
async def create_zip(request):
    user_id = request.form.get("user_id")
    pw = request.form.get("zip_password")
    redi = request.form.get("redirect", False)
    download_dir = request.app.config.DOWNLOAD_DIR
    # Create upload folder if doesn't exist
    if not os.path.exists(download_dir):
        os.makedirs(upload_dir)
    upload_dir = request.app.config.UPLOAD_DIR + "/" + user_id
    import subprocess
    filename = user_id + '.zip'
    subprocess.call(['zip', '-j', '-r', '-P'+pw, download_dir + "/" + filename, upload_dir])
    if redi:
        return redirect("/d/"+filename)
    return await file_stream(
        "downloads/" + filename,
        headers={'Content-type': 'application/zip', 'Content-Disposition': 'attachment', 'filename': '"'+filename+'"'},
        filename=filename
    )
    #return await file_stream(request.app.config.HOST_NAME+"d/"+user_id+".zip")


@file_bp.route("file/delete", methods=["POST"])
def rm_file_from_session(request):
    upload_dir = request.app.config.UPLOAD_DIR
    user_id = request.form.get("user_id")
    file_uuid = request.form.get("file_uuid")
    filename = request['session']['filenames'][file_uuid]
    file_path = upload_dir + "/" + user_id + "/" + filename
    if os.path.exists(file_path):
        os.remove(file_path)
    del request['session']['filenames'][file_uuid]
    return redirect('/?deleted_file')


def create_dirs(request, user_id=None):
    upload_dir = request.app.config.UPLOAD_DIR
    # Create upload folder if doesn't exist
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    if not(user_id):
        user_id = request['session']['user_id']
    user_dir = upload_dir + "/" + user_id
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return


@file_bp.route('/api/v1/file/process/<user_id>', methods=['DELETE'])
async def process_file_api_delete(request, user_id):
    user = await get_user(user_id)
    upload_dir = request.app.config.UPLOAD_DIR
    file_uuid = request.body
    filenames = user["filenames"]
    filename = filenames[file_uuid.decode()]
    del filenames[file_uuid.decode()]
    user = await User.update_one({'user_id':user['user_id']}, {'$set':{'filenames':filenames}})
    file_path = upload_dir + "/" + user_id + "/" + filename
    if os.path.exists(file_path):
        os.remove(file_path)
    else:
        print("could not remove " + file_path)
    return text("success")


@file_bp.route('/api/v1/file/process/<user_id>', methods=['POST', 'OPTIONS'])
async def process_file_api_post(request, user_id):
    create_dirs(request, user_id)
    upload_dir = request.app.config.UPLOAD_DIR
    user_dir = upload_dir + "/" + user_id
    file_fp = request.files.get('filepond')
    if not file_fp:
        return text("No file found.")
    elif not valid_file_type(file_fp.name, file_fp.type):
        return text("Invalid file type.")
    elif not valid_file_size(file_fp.body):
        return text("File too large.")
    else:
        filename = secure_filename(file_fp.name)
        file_path = f"{user_dir}/{filename}"
        user = await get_user(user_id)
        file_uuid = await add_file_to_db(user, filename)
        await write_file(file_path, file_fp.body)
        return text(file_uuid)


@file_bp.route("/upload", methods=["POST"])
async def process_upload(request):

    upload_dir = request.app.config.UPLOAD_DIR
    # Create upload folder if doesn't exist
    user_id = request['session']['user_id']
    user_dir = upload_dir + "/" + user_id
    create_dirs(request)

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
