from flask import Flask, render_template


def init_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()

    with app.app_context():
        # Include routes
        from . import entry, species, structure

        app._entries = entry.load_entries()

        return app


app = init_app()


@app.route("/")
def index_endpoint():
    return render_template("index.html")
