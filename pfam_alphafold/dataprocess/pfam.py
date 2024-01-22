import gzip

from .models import Entry


def parse_dat_file(file: str) -> list[Entry]:
    if file.lower().endswith(".gz"):
        _open = gzip.open
    else:
        _open = open

    entries = []
    with _open(file, mode="rt") as fh:
        for line in map(str.rstrip, fh):
            if line.startswith("# STOCKHOLM"):
                accession = name = descr = _type = None
            elif line == "//":
                entries.append(Entry(accession, name, descr, _type))
            else:
                # Assumes line starts with "#=GF"
                key, value = line[4:].strip().split(maxsplit=1)

                if key == "ID":
                    name = value
                elif key == "AC":
                    accession, _ = value.split(".")
                elif key == "DE":
                    descr = value
                elif key == "TP":
                    _type = value

    return entries
