import argparse

from pfam_alphafold.dataprocess import alphafold, database, interpro, uniprot


def prepare():
    parser = argparse.ArgumentParser(
        description="Prepare Pfam×AlphaFold data."
    )
    subparsers = parser.add_subparsers(required=True)

    subparser = subparsers.add_parser("alphafold",
                                      help="Index AlphaFold predictions.")
    subparser.add_argument("-p", dest="processes", type=int, default=1,
                           help="Number of workers, default: 1.")
    subparser.add_argument("indir", help="Input directory of TAR files.")
    subparser.add_argument("output", help="Output file.")
    subparser.set_defaults(func=parse_alphafold)

    subparser = subparsers.add_parser("pfam", help="Index Pfam matches.")
    subparser.add_argument("dat", help="Pfam-A dat file.")
    subparser.add_argument("xml", help="InterPro matches XML file.")
    subparser.add_argument("output", help="Output file.")
    subparser.set_defaults(func=parse_pfam)

    # subparser = subparsers.add_parser("predictions", help="Index predictions.")
    # subparser.add_argument("dat", help="Pfam-A dat file.")
    # subparser.add_argument("xml", help="InterPro extra matches XML file.")
    # subparser.add_argument("output", help="Output file.")
    # subparser.set_defaults(func=parse_predictions)

    subparser = subparsers.add_parser("uniprot",
                                      help="Index UniProtKB entries.")
    subparser.add_argument("sprot", help="UniProtKB/Swiss-Prot flat file.")
    subparser.add_argument("trembl", help="UniProtKB/TrEMBL flat file.")
    subparser.add_argument("output", help="Output file.")
    subparser.set_defaults(func=parse_uniprot)

    args = parser.parse_args()
    args.func(args)


def parse_alphafold(args):
    alphafold.extract(args.indir, args.output, processes=args.processes)


def parse_pfam(args):
    interpro.index_pfam(args.dat, args.xml, args.output)


def parse_predictions(args):
    interpro.index_predictions(args.dat, args.xml, args.output)


def parse_uniprot(args):
    uniprot.index(args.sprot, args.trembl, args.output)


def build():
    parser = argparse.ArgumentParser(
        description="Build the Pfam×AlphaFold database."
    )
    parser.add_argument("alphafold",
                        help="Path to AlphaFold store.")
    parser.add_argument("pfam",
                        help="Path to Pfam store.")
    parser.add_argument("uniprot",
                        help="Path to UniProtKB store.")
    parser.add_argument("database", help="Output database.")
    args = parser.parse_args()
    database.build(args.alphafold, args.pfam, args.uniprot, args.database)
