from sanic import Sanic
from sanic.response import json
from sanic_jinja2 import SanicJinja2


app = Sanic()
jinja = SanicJinja2(app)
app.config.from_envvar('MYAPP_SETTINGS')

@app.route("/")
async def test(request):
    print(app.config.UPLOAD_DIR)
    return jinja.render("index.html", request)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
