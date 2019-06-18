#Python
import os
from datetime import datetime

# 3rd party packages
from sanic import Sanic
from sanic.response import json
from sanic_jinja2 import SanicJinja2
from sanic_motor import BaseModel
from sanic_session import Session, MongoDBSessionInterface
from controllers.file import file_bp

app = Sanic()
app.blueprint(file_bp)
jinja = SanicJinja2(app)
app.config.from_envvar('MYAPP_SETTINGS')

BaseModel.init_app(app)
session = Session(app, interface=MongoDBSessionInterface(app))


@app.route("/", methods=["GET"])
async def front_page(request):
    return jinja.render("index.html", request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
