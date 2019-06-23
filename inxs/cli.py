# TODO documentation
# TODO allow passing arguments


import importlib
import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from shutil import copy2 as copy_file
from traceback import print_exc
from typing import Sequence

from delb import Document
from lxml import etree

from inxs import Transformation
from inxs.lib import dbg, logger, nfo


def parse_args(args: Sequence[str]) -> Namespace:
    parser = ArgumentParser()

    parser.add_argument(
        "--inplace",
        "-i",
        action="store_true",
        default=False,
        help="Write the result back to the input file.",
    )
    parser.add_argument(
        "--pretty",
        "-p",
        action="store_true",
        default=False,
        help='Prettifies the resulting document with indentations to be "human '
        'readable."',
    )
    parser.add_argument(
        "--recover",
        action="store_true",
        default=False,
        help="Let the parser try to process broken XML.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increases the logging level; twice for debug.",
    )
    # TODO help texts
    parser.add_argument("transformation", metavar="TRANSFORMATION")
    parser.add_argument("input", metavar="INPUT", type=Path)

    return parser.parse_args(args)


def setup_logging(verbosity: int) -> None:
    level = ("WARNING", "INFO", "DEBUG")[verbosity]
    console_log_handler = logging.StreamHandler(sys.stderr)
    console_log_handler.setLevel(level)
    logger.addHandler(console_log_handler)
    logger.setLevel(level)


def get_transformation(location: str) -> Transformation:
    # TODO allow use of contributed transformations
    if ":" in location:
        module_path, transformation_name = location.split(":")
    else:
        module_path, transformation_name = location, None

    if not module_path.endswith(".py"):
        module_path += ".py"
    module_path = (Path.cwd() / module_path).resolve()
    dbg(f"Transformation module path: {module_path}")

    dbg("Loading module.")
    module_spec = importlib.util.spec_from_file_location(
        "transformation_file", module_path
    )
    _module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(_module)

    dbg("Inspecting module.")
    transformation_objects = {
        k: v for k, v in vars(_module).items() if isinstance(v, Transformation)
    }

    if transformation_name is None:
        if "main" in transformation_objects:
            dbg("Selected symbol 'main' from module as transformation.")
            return transformation_objects["main"]
        else:
            name, instance = next((k, v) for k, v in transformation_objects.items())
            dbg(f"Selected symbol '{name}' from module as transformation.")
            return instance

    for instance in transformation_objects.values():
        if instance.name == transformation_name:
            dbg(
                f"Selected transformation named '{transformation_name}' from module "
                f"as transformation."
            )
            return instance

    dbg(f"Selected symbol '{transformation_name}' from module as transformation.")
    return transformation_objects[transformation_name]


def parse_file(args: Namespace) -> Document:
    dbg("Parsing file.")
    parser = etree.XMLParser(recover=args.recover)
    return Document(args.input, parser=parser)


def write_result(document: Document, args: Namespace) -> None:
    if args.inplace:
        dbg("Wrote result back to file.")
        document.save(args.input, pretty=args.pretty)
    else:
        document.write(sys.stdout.buffer, pretty=args.pretty)


def main(args: Sequence[str] = None) -> None:
    nfo("Starting")
    try:
        if args is None:
            args = sys.argv[1:]
        args = parse_args(args)
        setup_logging(args.verbose)
        dbg(f"Invoked with args: {args}")
        transformation = get_transformation(args.transformation)
        document = parse_file(args)
        if args.inplace:
            copy_file(args.input, args.input.with_suffix(".orig"))
            dbg("Saved document backup with suffix '.orig'")
        dbg("Applying transformation.")
        document.root = transformation(document.root)
        write_result(document, args)
    except Exception:
        print_exc()
        raise SystemExit(2)


if __name__ == "__main__":
    main()

__all__ = [main.__name__]
