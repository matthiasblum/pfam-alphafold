import sqlite3
from flask import current_app as app, g, request


def get_connection() -> sqlite3.Connection:
    con = getattr(g, '_connection', None)
    if con is None:
        con = g._connection = sqlite3.connect(app.config["DATABASE"])
    return con


@app.teardown_appcontext
def close_connection(exception):
    con = getattr(g, '_connection', None)
    if con is not None:
        con.close()


def get_order():
    order_by = order_dir = None

    index = request.args.get("order[0][column]")
    if index is not None:
        order_by = request.args[f"columns[{index}][data]"]

        if request.args["order[0][dir]"].lower() == "asc":
            order_dir = "ASC"
        else:
            order_dir = "DESC"

    return order_by, order_dir
