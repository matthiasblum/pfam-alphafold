FROM python:3.12-alpine
RUN apk update && apk upgrade && apk add --no-cache git sqlite

WORKDIR /app

RUN git clone https://github.com/matthiasblum/pfam-alphafold

WORKDIR /app/pfam-alphafold

RUN pip install .

RUN gunzip -c data/demo.sql.gz | sqlite3 data/demo.db

ENV FLASK_DATABASE="/app/pfam-alphafold/data/demo.db"

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "4", "pfam_alphafold.web:app"]