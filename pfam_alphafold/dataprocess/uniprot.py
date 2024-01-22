import gzip
import re

from . import io, models, store


def parse(file: str):
    if file.lower().endswith(".gz"):
        _open = gzip.open
    else:
        _open = open

    # Manual: https://web.expasy.org/docs/userman.html
    ox_reg = re.compile(r"NCBI_TaxID=(\d+)")

    with _open(file, mode="rt") as fh:
        for line in map(str.rstrip, fh):
            key = line[:2]
            value = line[5:]

            if key == "ID":
                cols = value.split()
                uniprot_id = cols[0]
                status = cols[1].rstrip(";")
                length = int(cols[2])
                entry = models.Protein(identifier=uniprot_id,
                                       length=length,
                                       reviewed=status == "Reviewed")
            elif key == "AC" and not entry.accession:
                entry.accession = value.split(";")[0]
            elif key == "DE":
                if value.startswith("Flags:") and "Fragment" in value:
                    entry.complete = False
            elif key == "OS":
                if entry.species:
                    entry.species += " " + value
                else:
                    entry.species = value
            if key == "OC":
                for node in value.rstrip(".").split(";"):
                    entry.lineage.append(node.strip())
            elif key == "OX":
                entry.taxon_id = int(ox_reg.match(value).group(1))
            elif key == "KW":
                if not entry.ref_proteome:
                    for e in value.rstrip(".").split(";"):
                        if e.strip() == "Reference proteome":
                            entry.ref_proteome = True
                            break
            elif key == "SQ":
                cols = value.split()
                entry.crc64 = cols[5]
            elif key == "//":
                entry.clean()
                yield entry


def index(sprot_file: str, trembl_file: str, output: str):
    io.log("parsing UniProtKB entries")

    sstore = store.SimpleStore(output, "w")
    n = 0
    for file in [sprot_file, trembl_file]:
        for entry in parse(file):
            sstore.add(entry.accession, entry)
            n += 1

            if n % 1e7 == 0:
                io.log(f"\t{n:,}")

    io.log(f"\t{n:,}")
    io.log("indexing")
    sstore.build(verbose=True)
    io.log("complete")
