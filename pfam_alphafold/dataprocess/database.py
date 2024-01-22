import json
import math
import os
import sqlite3
import sys

from . import io, store
from .models import Entry


def build(alphafold_file: str, pfam_file: str, uniprot_file: str,
          database: str):
    for path, cmd in [(alphafold_file, "alphafold"),
                      (pfam_file, "pfam"),
                      (uniprot_file, "uniprot")]:
        if not os.path.isfile(path):
            print(f"Error: {path} not found. "
                  f"Run 'pfafindex {cmd}' to create it.",
                  file=sys.stderr)
            sys.exit(1)

    io.log("building database")
    proteins = store.SimpleStore(uniprot_file)
    pfams = store.SimpleStore(pfam_file)
    structures = store.SimpleStore(alphafold_file)

    try:
        os.unlink(database)
    except FileNotFoundError:
        pass

    con = sqlite3.connect(database, isolation_level="DEFERRED")
    cur = con.cursor()
    cur.execute("PRAGMA synchronous = OFF")
    cur.execute("PRAGMA journal_mode = OFF")
    cur.execute(
        """
        CREATE table uniprot (
            id TEXT NOT NULL,
            reviewed INTEGER NOT NULL,
            complete INTEGER NOT NULL,
            superkingdom TEXT NOT NULL,
            taxon_id INTEGER NOT NULL,
            species TEXT NOT NULL,
            length INTEGER NOT NULL,
            score REAL NOT NULL,
            in_pfam INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE table entry (
            id TEXT NOT NULL,
            name TEXT,
            description TEXT,
            num_alphafold INTEGER NOT NULL,
            dom_score REAL NOT NULL,
            glo_score REAL NOT NULL,
            distributions TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE table pfam2uniprot (
            entry_id TEXT NOT NULL,
            protein_id TEXT NOT NULL,
            reviewed INTEGER NOT NULL,
            complete INTEGER NOT NULL,
            superkingdom TEXT NOT NULL,
            taxon_id INTEGER NOT NULL,
            species TEXT NOT NULL,
            length INTEGER NOT NULL,
            dom_score REAL NOT NULL,
            glo_score REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE table species (
            id TEXT NOT NULL,
            name TEXT NOT NULL,
            superkingdom TEXT NOT NULL,
            num_alphafold INTEGER NOT NULL
        )
        """
    )

    af_entry = Entry(accession="alphafold",
                     name="AlphaFold",
                     description="AlphaFold",
                     type="alphafold")
    entries = {}
    species = {}
    superkingdoms = {
        "Archaea": "arch",
        "Bacteria": "bact",
        "Eukaryota": "euk",
    }
    other_superkingdoms = "others"
    uniprot_params = []
    pfam2uniprot_params = []

    progress = 0
    step = milestone = 10000000
    for uniprot_acc, protein in proteins.items():
        plddt = []
        try:
            fragments = structures[uniprot_acc]
        except KeyError:
            pass
        else:
            if len(fragments) == 1:
                fragment, scores, crc64 = fragments[0]
                if fragment == "F1" and protein.crc64 == crc64:
                    plddt = scores

        if plddt:
            glo_avg_plddt = sum(plddt) / len(plddt)

            pfam_hits = []
            try:
                _protein = pfams[uniprot_acc]
            except KeyError:
                pass
            else:
                if protein.crc64 == _protein.crc64:
                    pfam_hits = _protein.hits

            # disorder_regions = []
            # pfamn_hits = []
            # try:
            #     _protein = predictions[uniprot_acc]
            # except KeyError:
            #     pass
            # else:
            #     if protein.crc64 == _protein.crc64:
            #         for match in _protein.hits:
            #             if match["id"] == "MobiDB-lite":
            #                 disorder_regions.append(match)
            #             else:
            #                 pfamn_hits.append(match)

            try:
                superkingdom = superkingdoms[protein.lineage[0]]
            except KeyError:
                superkingdom = other_superkingdoms

            uniprot_params.append((
                uniprot_acc,
                1 if protein.reviewed else 0,
                1 if protein.complete else 0,
                superkingdom,
                protein.taxon_id,
                protein.species,
                protein.length,
                glo_avg_plddt,
                1 if pfam_hits else 0
            ))
            if len(uniprot_params) == 100000:
                cur.executemany(
                    "INSERT INTO uniprot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    uniprot_params
                )
                uniprot_params.clear()

            try:
                species[protein.taxon_id][3] += 1
            except KeyError:
                species[protein.taxon_id] = [
                    protein.taxon_id,
                    protein.species,
                    superkingdom,
                    1
                ]

            af_entry.num_alphafold += 1
            key = f"glo_{superkingdom}"
            index = math.floor(glo_avg_plddt)
            af_entry.dists[key][index] += 1

            if protein.complete:
                af_entry.dists[f"{key}_nofrags"][index] += 1

            for match in pfam_hits:
                try:
                    entry = entries[match["id"]]
                except KeyError:
                    entry = entries[match["id"]] = Entry.fromdict(match)

                entry.num_alphafold += 1
                dom_plddt = [None] * protein.length

                for start, end in match["locations"]:
                    for i in range(start - 1, end):
                        dom_plddt[i] = plddt[i]

                dom_plddt = [v for v in dom_plddt if v is not None]
                dom_avg_plddt = sum(dom_plddt) / len(dom_plddt)
                entry.glo_score += glo_avg_plddt
                entry.dom_score += dom_avg_plddt

                for prefix, score in [("glo", glo_avg_plddt),
                                      ("dom", dom_avg_plddt)]:
                    key = f"{prefix}_{superkingdom}"
                    index = math.floor(score)
                    entry.dists[key][index] += 1

                    if protein.complete:
                        entry.dists[f"{key}_nofrags"][index] += 1

                pfam2uniprot_params.append((
                    entry.accession,
                    uniprot_acc,
                    1 if protein.reviewed else 0,
                    1 if protein.complete else 0,
                    superkingdom,
                    protein.taxon_id,
                    protein.species,
                    protein.length,
                    dom_avg_plddt,
                    glo_avg_plddt
                ))
                if len(pfam2uniprot_params) == 100000:
                    cur.executemany(
                        """
                        INSERT INTO pfam2uniprot 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        pfam2uniprot_params
                    )
                    pfam2uniprot_params.clear()

        progress += 1
        if progress == milestone:
            io.log(f"\t{progress:,}")
            milestone += step

    if uniprot_params:
        cur.executemany(
            "INSERT INTO uniprot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            uniprot_params
        )
        uniprot_params.clear()

    if pfam2uniprot_params:
        cur.executemany(
            """
            INSERT INTO pfam2uniprot 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            pfam2uniprot_params
        )
        pfam2uniprot_params.clear()

    io.log(f"\t{progress:,}")

    params = [(
        af_entry.accession,
        af_entry.name,
        af_entry.description,
        af_entry.num_alphafold,
        0,
        0,
        json.dumps(af_entry.dists)
    )]
    for entry in entries.values():
        try:
            dom_score = entry.dom_score / entry.num_alphafold
            glo_score = entry.glo_score / entry.num_alphafold
        except ZeroDivisionError:
            dom_score = glo_score = 0

        params.append((
            entry.accession,
            entry.name,
            entry.description,
            entry.num_alphafold,
            dom_score,
            glo_score,
            json.dumps(entry.dists)
        ))

    cur.executemany(
        "INSERT INTO entry VALUES (?, ?, ?, ?, ?, ?, ?)",
        params
    )

    cur.executemany(
        "INSERT INTO species VALUES (?, ?, ?, ?)",
        (v for v in species.values())
    )

    con.commit()

    io.log("indexing")
    for i, columns in enumerate([
        ("entry_id",),
        ("entry_id", "complete"),
        ("entry_id", "superkingdom"),
        ("entry_id", "complete", "superkingdom")
    ]):
        name = f"i_pfam2uniprot_{i+1}"
        sql = f"CREATE INDEX {name} ON pfam2uniprot ({','.join(columns)})"
        cur.execute(sql)

    cur.execute("CREATE UNIQUE INDEX u_entry ON entry (id)")
    cur.execute("CREATE UNIQUE INDEX u_uniprot ON uniprot (id)")
    cur.close()
    con.close()

    io.log("complete")
