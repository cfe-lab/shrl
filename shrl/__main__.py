'''Entrypoint for use from the console
'''
import argparse
import logging

import shrl.handlers

DESC = '''The SHARED data regularity checker and load helper.'''

parser = argparse.ArgumentParser(
    prog='shrl',
    description=DESC,
)
parser.set_defaults(handler=parser.print_help)
parser.add_argument(
    "--verbose",
    "-v",
    action="store_true",
    help="Enable verbose logging",
)
parser.add_argument(
    "--with-metadata",
    help=("Load Collaborator, Reference, and/or SourceStudy records from a "
          ".conf file and associate them with the loaded records"),
)

subparsers = parser.add_subparsers(title='commands')

check = subparsers.add_parser(
    name='check',
    help='Check data files for consistency',
)
check.add_argument(
    'directory',
    help='Directory to search for datafiles',
)
check.set_defaults(handler=shrl.handlers.check)

report = subparsers.add_parser(
    name='report',
    help='Statistics on the contents of data files',
)
report.add_argument(
    'directory',
    help='Directory to search for datafiles',
)
report.set_defaults(handler=shrl.handlers.report)

load = subparsers.add_parser(
    name='load',
    help='Load submitted data into a database',
)
load.add_argument(
    'directory',
    help='Directory to search for datafiles',
)
load.add_argument(
    'database',
    help='Database to load data into (as a database string)',
)
load.add_argument(
    "--init-db",
    action="store_true",
    help=("Initialize the database according to the SHARED schema (for "
          "starting a new database)."),
)
load.add_argument(
    "--load-regimens",
    action="store_true",
    help=("Insert Regimen and RegimenDrugInclusion records for the standard "
          "regimens (suggested when starting a new database)."),
)
load.set_defaults(handler=shrl.handlers.load)


def main() -> None:
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level="INFO")
    logging.info(f"Using handler {args.handler} with args: {args}")
    args.handler(args)
