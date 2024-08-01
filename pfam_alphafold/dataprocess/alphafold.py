import glob
import gzip
import json
import os
import multiprocessing as mp
import re
import tarfile
from tempfile import mkstemp

from crc64iso import crc64iso

from . import io, store


def extract(indir: str, output: str, processes: int = 1, version: int = 4):
    io.log("processing AlphaFold predictions")

    output = os.path.abspath(output)
    inqueue = mp.Queue()
    outqueue = mp.Queue()

    workers = []
    for _ in range(max(1, processes - 1)):
        fd, path = mkstemp(prefix=os.path.basename(output),
                           dir=os.path.dirname(output))
        os.close(fd)
        p = mp.Process(target=worker,
                       args=(inqueue, version, path, outqueue))
        p.start()
        workers.append(p)

    path = os.path.join(indir, "**", f"proteome-tax_id-*_v{version}.tar")
    for file in glob.iglob(path, recursive=True):
        inqueue.put(file)

    for _ in workers:
        inqueue.put(None)

    progress = 0
    milestone = step = 1e7
    stores = []
    running = len(workers)
    while running > 0:
        obj = outqueue.get()
        if isinstance(obj, int):
            progress += obj

            if progress >= milestone:
                io.log(f"{progress:,} predictions processed")
                milestone += step
        else:
            stores.append(obj)
            running -= 1

    io.log(f"{progress:,} predictions processed")
    for p in workers:
        p.join()

    io.log("building final store")
    sstore = store.SimpleStore(output, mode="w")
    sstore.build(iterable=[iter_temp_stores(f) for f in stores],
                 buffersize=1000,
                 verbose=True)
    for f in stores:
        os.unlink(f)

    io.log("complete")


def worker(inqueue: mp.Queue, version: int, output: str, outqueue: mp.Queue):
    sstore = store.SimpleStore(output, mode="w", tempbuffersize=100000)

    for file in iter(inqueue.get, None):
        predictions = extract_tar(file, version)
        for accession, fragments in predictions.items():
            sstore.add(accession, fragments)

        outqueue.put(len(predictions))

    sstore.build()
    outqueue.put(output)


def extract_tar(file: str, version: int = 4) -> dict[str, list[tuple]]:
    """
    In the case of proteins longer than 2700 amino acids (aa),
    AlphaFold provides 1400aa long, overlapping fragments.
    For example, Titin has predicted fragment structures named
    as Q8WZ42-F1 (residues 1-1400), Q8WZ42-F2 (residues 201-1600), etc.
    These fragments are currently only available
    for the human proteome in these proteome archive files,
    not on the website.
    (https://alphafold.ebi.ac.uk/download)
    """
    regex = re.compile(r"(AF-[A-Z\d]+-F\d+)-confidence_v(\d+).json.gz")
    predictions = {}
    with tarfile.open(file) as tar:
        for name in tar.getnames():
            match = regex.fullmatch(name)

            if match:
                model_id, model_version = match.groups()

                if int(model_version) != version:
                    continue

                _, accession, fragment = model_id.split("-")

                br = tar.extractfile(name)
                content = br.read()
                json_str = gzip.decompress(content).decode("utf-8")
                data = json.loads(json_str)
                # Other keys: residueNumber, confidenceCategory
                scores = data["confidenceScore"]

                name = f"{model_id}-model_v{model_version}.cif.gz"
                br = tar.extractfile(name)
                content = br.read()
                cif = gzip.decompress(content).decode("utf-8")
                sequence, scores_alt = parse_cif(cif)

                if len(sequence) != len(scores) or scores != scores_alt:
                    io.log(f"error in {name} ({file})")
                    continue

                crc64 = crc64iso.crc64(sequence)
                try:
                    obj = predictions[accession]
                except KeyError:
                    obj = predictions[accession] = []

                obj.append((fragment, scores, crc64))

    return predictions


def parse_cif(cif: str) -> tuple[str, list[float]]:
    sequence = ""
    scores = []
    prev_res_num = None

    for line in cif.splitlines():
        if line[:4] == "ATOM":
            values = line.split()
            res_num = int(values[23])

            if res_num != prev_res_num:
                sequence += values[24]
                scores.append(float(values[14]))
                prev_res_num = res_num

    return sequence.upper(), scores


def iter_temp_stores(file: str):
    sstore = store.SimpleStore(file, mode="r")
    yield from sstore.items()
