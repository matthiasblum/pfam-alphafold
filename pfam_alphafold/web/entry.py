import json
from flask import current_app as app, jsonify, render_template, request

from .utils import get_connection, get_order


@app.route("/entry/<string:entry_id>/")
def entry_endpoint(entry_id: str):
    return render_template("entry.html", accession=entry_id)


def load_entries() -> list[tuple]:
    entries = []

    con = get_connection()
    for row in con.execute(
            """
            SELECT id, name, description, num_alphafold, dom_score, glo_score, 
                   distributions
            FROM entry
            WHERE id != 'alphafold'
            """
    ):
        entry_id, name, descr, n_predictions, dom_score, glo_score, s = row
        data = json.loads(s)
        glo_hist = [0] * 100
        dom_hist = [0] * 100

        for key, value in data.items():
            if key.endswith("_nofrags"):
                continue
            elif key.startswith("glo_"):
                dst = glo_hist
            elif key.startswith("dom_"):
                dst = dom_hist
            else:
                continue

            for i, v in enumerate(value):
                dst[i] += v

        entries.append((entry_id, name, descr, n_predictions, glo_score,
                        dom_score, dom_score - glo_score,
                        glo_hist, dom_hist))

    return entries


@app.route("/api/entries/")
def api_entries_endpoint():
    draw = int(request.args.get("draw", "0"))
    search = request.args.get("search[value]", "").strip().lower()
    start = int(request.args.get("start", "0"))
    length = int(request.args.get("length", str(len(app._entries))))
    order_by, order_dir = get_order()
    summary = request.args.get("summary", "false").lower() == "true"

    if search:
        entries = []
        for e in app._entries:
            for v in e[:3]:
                if v and search in v.lower():
                    entries.append(e)
                    break
    else:
        entries = app._entries

    reverse = order_dir == "DESC"
    if order_by == "name":
        entries.sort(key=lambda x: x[1], reverse=reverse)
    elif order_by == "description":
        entries.sort(key=lambda x: x[2], reverse=reverse)
    elif order_by == "count":
        entries.sort(key=lambda x: x[3], reverse=reverse)
    elif order_by == "glo_score":
        entries.sort(key=lambda x: x[4], reverse=reverse)
    elif order_by == "dom_score":
        entries.sort(key=lambda x: x[5], reverse=reverse)
    elif order_by == "delta":
        entries.sort(key=lambda x: abs(x[6]), reverse=reverse)
    else:
        entries.sort(key=lambda x: x[0], reverse=reverse)

    results = []
    for (entry_id, name, descr, count, glo_score, dom_score, delta, glo_hist,
         dom_hist) in entries[start:start+length]:
        results.append({
            "id": entry_id,
            "name": name,
            "description": descr,
            "count": count,
            "glo_score": glo_score,
            "glo_hist": {
                "p90": sum(glo_hist[90:]),
                "p70": sum(glo_hist[70:90]),
                "p50": sum(glo_hist[50:70]),
                "m50": sum(glo_hist[:50]),
            } if summary else glo_hist,
            "dom_score": dom_score,
            "dom_hist": {
                "p90": sum(dom_hist[90:]),
                "p70": sum(dom_hist[70:90]),
                "p50": sum(dom_hist[50:70]),
                "m50": sum(dom_hist[:50]),
            } if summary else dom_hist,
            "delta": delta
        })

    return jsonify({
        "draw": draw,
        "recordsTotal": len(app._entries),
        "recordsFiltered": len(entries),
        "data": results,
    })


@app.route("/api/entry/<string:entry_id>/alphafold/")
def api_entry_structures_endpoint(entry_id):
    dom_score = int(request.args.get("dom_score", "-1"))
    draw = int(request.args.get("draw", "0"))
    fragment = request.args.get("fragment", "").lower()
    glo_score = int(request.args.get("glo_score", "-1"))
    length = int(request.args.get("length", "20"))
    species = request.args.get("species", "")
    reviewed = request.args.get("reviewed", "").lower()
    start = int(request.args.get("start", "0"))
    superkingdom = request.args.get("origin", "").lower()
    order_by, order_dir = get_order()

    filter_by = ["entry_id = ?"]
    params = [entry_id]

    if superkingdom in ("arch", "bact", "euk", "others"):
        filter_by.append("superkingdom = ?")
        params.append(superkingdom)

    if glo_score >= 0:
        filter_by.append("(glo_score >= ? AND glo_score < ?)")
        params += [glo_score, glo_score + 1]
    elif dom_score >= 0:
        filter_by.append("(dom_score >= ? AND dom_score < ?)")
        params += [dom_score, dom_score + 1]

    if fragment == "true":
        filter_by.append("complete = 0")
    elif fragment == "false":
        filter_by.append("complete = 1")

    if reviewed == "true":
        filter_by.append("reviewed = 1")
    elif reviewed == "false":
        filter_by.append("reviewed = 0")

    if species:
        filter_by.append("taxon_id = ?")
        params.append(int(species))

    sql = f"""
        SELECT COUNT(*)
        FROM pfam2uniprot 
        WHERE {' AND '.join(filter_by)}
    """

    con = get_connection()
    num_filtered, = con.execute(sql, params).fetchone()

    results = []
    if num_filtered > 0:
        if order_by and order_dir:
            if order_by == "id":
                order_by = "protein_id"
            elif order_by == "delta":
                order_by = "ABS(dom_score-glo_score)"

            order_by = f"ORDER BY {order_by} {order_dir}"
        else:
            order_by = ""

        if start >= 0 and length > 0:
            limit = "LIMIT ?, ?"
            params += [start, length]
        else:
            limit = ""

        sql = f"""
            SELECT protein_id, reviewed, complete, length, species, 
                   glo_score, dom_score
            FROM pfam2uniprot
            WHERE {' AND '.join(filter_by)}
            {order_by}
            {limit}
        """

        for row in con.execute(sql, params):
            results.append({
                "id": row[0],
                "reviewed": row[1] != 0,
                "fragment": row[2] == 0,
                "length": row[3],
                "species": row[4],
                "glo_score": row[5],
                "dom_score": row[6],
            })

    n = 0
    for e in app._entries:
        if e[0].lower() == entry_id.lower():
            n = e[3]
            break

    return jsonify({
        "draw": draw,
        "recordsTotal": n,
        "recordsFiltered": num_filtered,
        "data": results,
    })


@app.route("/api/entry/<string:entry_id>/")
def api_entry_endpoint(entry_id: str):
    con = get_connection()
    row = con.execute(
        """
        SELECT name, description, num_alphafold, glo_score, dom_score, 
               distributions
        FROM entry
        WHERE id = ?
        """,
        [entry_id]
    ).fetchone()

    results = []
    if row:
        results.append({
            "id": entry_id,
            "name": row[0],
            "description": row[1],
            "count": row[2],
            "glo_score": row[3],
            "dom_score": row[4],
            "distributions": json.loads(row[5])
        })

    return jsonify({"results": results})
