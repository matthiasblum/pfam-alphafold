import gzip
import re
from xml.etree import ElementTree

from . import io, models, pfam, store


def parse_xml(file: str):
    if file.lower().endswith(".gz"):
        _open = gzip.open
    else:
        _open = open

    with _open(file, mode="rt") as fh:
        reg = re.compile(r"<protein")
        buffer = ""
        i = -1
        while chunk := fh.read(1000):
            buffer += chunk

            for m in reg.finditer(buffer):
                j = m.start()

                if j > i >= 0:
                    try:
                        yield ElementTree.fromstring(buffer[i:j])
                    except Exception as exc:
                        print(i, j, buffer[i:j])
                        raise exc

                i = j

            if i >= 0:
                buffer = buffer[i:]
                i = 0

        j = re.search(r"</interpro(extra|match)>", buffer).start()
        yield ElementTree.fromstring(buffer[i:j])


def index_pfam(dat_file: str, xml_file: str, output: str):
    io.log("loading Pfam families")
    families = {}
    for fam in pfam.parse_dat_file(dat_file):
        families[fam.accession] = fam

    io.log("parsing Pfam matches")
    sstore = store.SimpleStore(output, "w")

    n = 0
    for elem in parse_xml(xml_file):
        uniprot_acc = elem.attrib["id"]
        if "-" in uniprot_acc:
            continue

        protein = models.Protein(identifier=elem.attrib["name"],
                                 length=int(elem.attrib["length"]),
                                 accession=uniprot_acc,
                                 crc64=elem.attrib["crc64"])
        for match in elem.findall("match"):
            match_id = match.attrib["id"]
            try:
                family = families[match_id]
            except KeyError:
                continue
            else:
                locations = []
                for loc in match.findall("lcn"):
                    fragments = loc.get("fragments")
                    if fragments:
                        for fragment in fragments.split(","):
                            start, end, _ = fragment.split("-")
                            locations.append((int(start), int(end)))
                    else:
                        locations.append((int(loc.attrib["start"]),
                                          int(loc.attrib["end"])))

                protein.hits.append({
                    "id": match_id,
                    "name": family.name,
                    "description": family.description,
                    "type": family.type,
                    "locations": locations
                })

        if protein.hits:
            sstore.add(protein.accession, protein)

        n += 1
        if n % 1e7 == 0:
            io.log(f"\t{n:,}")

    io.log(f"\t{n:,}")
    io.log("indexing")
    sstore.build(verbose=True)
    io.log("complete")


def index_predictions(dat_file: str, xml_file: str, output: str):
    io.log("loading Pfam families")
    families = {}
    for fam in pfam.parse_dat_file(dat_file):
        families[fam.accession] = fam

    io.log("parsing predictions")
    sstore = store.SimpleStore(output, "w")

    n = 0
    for elem in parse_xml(xml_file):
        uniprot_acc = elem.attrib["id"]
        if "-" in uniprot_acc:
            continue

        protein = models.Protein(identifier=elem.attrib["name"],
                                 length=int(elem.attrib["length"]),
                                 accession=uniprot_acc,
                                 crc64=elem.attrib["crc64"])
        for match in elem.findall("match"):
            database = match.attrib["dbname"]
            locations = []
            if database == "MOBIDBLT":
                match_id = "MobiDB-lite"
                for loc in match.findall("lcn"):
                    if (loc.attrib["sequence-feature"] ==
                            "Consensus Disorder Prediction"):
                        locations.append((int(loc.attrib["start"]),
                                          int(loc.attrib["end"])))

                name = descr = None
                _type = "Disorder Prediction"
            elif database == "PFAM-N":
                match_id = match.attrib["id"]
                for loc in match.findall("lcn"):
                    locations.append((int(loc.attrib["start"]),
                                      int(loc.attrib["end"])))

                try:
                    family = families[match_id]
                except KeyError:
                    name = descr = _type = None
                else:
                    name = family.name
                    descr = family.description
                    _type = family.type
            else:
                continue

            protein.hits.append({
                "id": match_id,
                "name": name,
                "description": descr,
                "type": _type,
                "locations": locations
            })

        if protein.hits:
            sstore.add(protein.accession, protein)

        n += 1
        if n % 1e7 == 0:
            io.log(f"{n:,} proteins processed")

    io.log(f"{n:,} proteins processed")
    sstore.build(verbose=True)
    io.log("complete")
