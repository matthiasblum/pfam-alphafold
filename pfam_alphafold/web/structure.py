from flask import current_app as app, jsonify, render_template, request

from .utils import get_connection, get_order


@app.route("/structure/<string:entry_id>/")
def structure_endpoint(entry_id: str):
    return render_template("structure.html", entry_id=entry_id)


@app.route("/structures/")
def structures_endpoint():
    return render_template("structures.html")


@app.route("/api/structures/")
def api_structures_endpoint():
    draw = int(request.args.get("draw", "0"))
    entries = request.args.get("entries", "").lower()
    fragment = request.args.get("fragment", "").lower()
    length = int(request.args.get("length", "20"))
    species = int(request.args.get("species", "0"))
    reviewed = request.args.get("reviewed", "").lower()
    score = int(request.args.get("score", "-1"))
    start = int(request.args.get("start", "0"))
    superkingdom = request.args.get("origin", "").lower()
    order_by, order_dir = get_order()

    filter_by = []
    params = []
    if score >= 0:
        filter_by.append("score >= ? AND score < ?")
        params += [score, score + 1]

    if superkingdom in ("arch", "bact", "euk", "others"):
        filter_by.append("superkingdom = ?")
        params.append(superkingdom)

    if fragment == "true":
        filter_by.append("complete = 0")
    elif fragment == "false":
        filter_by.append("complete = 1")

    if reviewed == "true":
        filter_by.append("reviewed = 1")
    elif reviewed == "false":
        filter_by.append("reviewed = 0")

    if entries == "true":
        filter_by.append("in_pfam = 1")
    elif entries == "false":
        filter_by.append("in_pfam = 0")

    if species > 0:
        filter_by.append("taxon_id = ?")
        params.append(species)

    if filter_by:
        filter_by = f"WHERE {' AND '.join(filter_by)}"
    else:
        filter_by = ""

    con = get_connection()

    if length > 0:
        sql = f"SELECT COUNT(*) FROM uniprot {filter_by}"
        total_count, = con.execute(sql, params).fetchone()
    else:
        total_count = -1

    results = []
    if total_count != 0:
        if order_by and order_dir:
            order_by = f"ORDER BY {order_by} {order_dir}"
        else:
            order_by = ""

        if start >= 0 and length > 0:
            limit = "LIMIT ?, ?"
            params += [start, length]
        else:
            limit = ""

        sql = f"""
            SELECT id, reviewed, complete, species, length, score, in_pfam
            FROM uniprot
            {filter_by}
            {order_by}
            {limit}
        """

        for row in con.execute(sql, params):
            results.append({
                "id": row[0],
                "reviewed": row[1] != 0,
                "fragment": row[2] == 0,
                "organism": row[3],
                "length": row[4],
                "score": row[5],
                "in_pfam": row[6] != 0
            })

    return jsonify({
        "draw": draw,
        "recordsTotal": total_count,
        "recordsFiltered": total_count,
        "data": results,
    })
