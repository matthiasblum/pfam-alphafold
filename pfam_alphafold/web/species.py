from flask import current_app as app, jsonify, request

from .utils import get_connection


@app.route("/api/species/")
def api_species_endpoint():
    ids = set(request.args.getlist("id", type=int))

    if ids:
        filter_by = f"WHERE id IN ({','.join('?' for _ in ids)})"
        params = list(ids)
    else:
        filter_by = ""
        params = []

    con = get_connection()

    results = []
    columns = ("id", "name", "count")
    for row in con.execute(f"SELECT id, name, num_alphafold "
                           f"FROM species {filter_by}", params):
        results.append(dict(zip(columns, row)))

    return jsonify(results)
