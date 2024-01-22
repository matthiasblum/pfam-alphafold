# Pfam × AlphaFold

This project leverages UniProt, Pfam, and AlphaFold data to provide 
a comprehensive overview of Pfam matches against UniProt proteins 
and utilizes AlphaFold's pLDDT scores to calculate an average domain pLDDT score 
for each Pfam family.

## Getting started

Install the package:

```shell
$ pip install git+https://github.com/matthiasblum/pfam-alphafold.git
```

## Preparing data

The following sections explain how to obtain and pre-process data in order to build the Pfam×AlphaFold database.
Steps are independent and can be run in parallel.

### AlphaFold

Prerequisite: directory of predictions grouped in one `tar` archive per proteome. 
See [Bulk download](https://github.com/google-deepmind/alphafold/blob/main/afdb/README.md#bulk-download) 
from the AlphaFold Protein Structure Database GitHub repository to learn how to download these archives.

Extract and index pLDDT scores:

```shell
$ pfafindex alphafold [-p N] INDIR OUTPUT
```

Arguments:

* `-p N`: Use up to `N` processors (default: 1).
* `INDIR`: Directory of individual `tar` archives.
* `OUTPUT`: Output file of indexed AlphaFold pLDDT scores.

With `-p 16`, it took about 50 hours and 23 GB of memory to complete. The output file is about 600 GB big.

### UniProtKB

Prerequisites:

* UniProtKB/Swiss-Prot flat file (`uniprot_sprot.dat.gz`)
* UniProtKB/TrEMBL flat file (`uniprot_trembl.dat.gz`)

You can obtain the most recent version of these files from UniProt's FTP site:

```shell
$ wget https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz
$ wget https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.dat.gz
```

Index UniProtKB entries:

```shell
$ pfafindex uniprot uniprot_sprot.dat.gz uniprot_trembl.dat.gz OUTPUT
```

Arguments:

* `uniprot_sprot.dat.gz`: UniProtKB/Swiss-Prot flat file.
* `uniprot_trembl.dat.gz`: UniProtKB/TrEMBL flat file.
* `OUTPUT`: Output file of indexed UniProtKB entries.

Runtime: ~14 hours; memory: ~2 GB; output file: ~60 GB.

### Pfam

Prerequisites:

* Pfam summary flat file (`Pfam-A.hmm.dat.gz`)
* InterPro matches XML file (`match_complete.xml.gz`)

You can obtain the most recent version of these files from the InterPro's and Pfam's FTP sites:

```shell
$ wget https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.dat.gz
$ wget https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/match_complete.xml.gz
```

Index Pfam entries:

```shell
$ pfafindex pfam Pfam-A.hmm.dat.gz match_complete.xml.gz OUTPUT
```

Arguments:

* `Pfam-A.hmm.dat.gz`: Pfam summary flat file.
* `match_complete.xml.gz`: InterPro matches XML file.
* `OUTPUT`: Output file of indexed UniProtKB entries with Pfam matches.

Runtime: ~16 hours; memory: ~2 GB; output file: ~50 GB.

## Building the database

```shell
$ pfafbuild alphafold.dat pfam.dat uniprot.dat pfam-alphafold.db
```

Arguments:

* `alphafold.dat`: File of indexed AlphaFold pLDDT scores.
* `pfam.dat`: File of indexed UniProtKB entries with Pfam matches.
* `uniprot.dat`: File of indexed UniProtKB entries.
* `pfam-alphafold.db`: Output SQLite3 database.

Runtime: ~11 hours; memory: ~2 GB; output file: ~50 GB.

## Web application

Set the `FLASK_DATABASE` environment variable to the path 
of the SQLite3 database built with `pfafbuild`, then start the web server:

```shell
$ export FLASK_DATABASE="/path/to/pfam-alphafold.db"
$ gunicorn -b 0.0.0.0:8000 -w 4 pfam_alphafold.web:app
```

Now head over http://localhost:8000/ to access the web application.

### Demo database

This project includes data for a demo database (~800k proteins from key species and model organisms).

Re-create the database with the following command:

```shell
$ gunzip -c data/demo.sql.gz | sqlite3 data/demo.db
```

### Docker image

Alternatively, the web application with the demo database can be run using Docker.

To build the image, run:

```shell
$ docker build -t pfam-alphafold .
```

Once the image is built, you can run the container:

```shell
$ docker run --rm -p 8000:8000 pfam-alphafold
```

Now, the web application should be accessible at http://localhost:8000/.
