from setuptools import setup, find_packages

setup(
   name="pfam-alphafold",
   version="1.0.0",
   author="Matthias Blum",
   author_email="mblum@ebi.ac.uk",
   description="Build a SQLite3 database incorporating Pfam families and "
               "AlphaFold-predicted protein structures, "
               "with sequences matching those of Pfam families.",
   url="https://github.com/matthiasblum/pfam-alphafold",
   packages=find_packages(),
   include_package_data=True,
   zip_safe=False,
   install_requires=[
      "crc64iso==0.0.2",
      "flask~=3.0.0",
      "gunicorn~=21.2.0"
   ],
   entry_points={
      "console_scripts": [
         "pfafindex=pfam_alphafold.cli:prepare",
         "pfafbuild=pfam_alphafold.cli:build",
      ],
   },
)
