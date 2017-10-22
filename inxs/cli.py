# TODO documentation
# TODO allow passing arguments


from argparse import ArgumentParser, Namespace
from traceback import print_exc
import importlib.util
import logging
from pathlib import Path
from shutil import copy2 as copy_file
import sys
from typing import Sequence

from lxml import etree

from inxs import Transformation
from inxs.lib import dbg, logger, nfo


def parse_args(args: Sequence[str]) -> Namespace:
    parser = ArgumentParser()

    parser.add_argument('--pretty', action='store_true', default=False)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('transformation')
    parser.add_argument('target')

    return parser.parse_args(args)


def setup_logging(verbosity: int) -> None:
    level = ('WARNING', 'INFO', 'DEBUG')[verbosity]
    console_log_handler = logging.StreamHandler(sys.stdout)
    console_log_handler.setLevel(level)
    logger.addHandler(console_log_handler)
    logger.setLevel(level)


def get_transformation(location: str) -> Transformation:
    # TODO allow use of contributed transformations
    if ':' in location:
        module_path, transformation_name = location.split(':')
    else:
        module_path, transformation_name = location, None

    if not module_path.endswith('.py'):
        module_path += '.py'
    module_path = (Path.cwd() / module_path).resolve()
    dbg(f'Transformation module path: {module_path}')

    dbg('Loading module.')
    module_spec = importlib.util.spec_from_file_location('transformation_file', module_path)
    _module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(_module)

    dbg('Inspecting module.')
    transformation_objects = {k: v for k, v in vars(_module).items()
                              if isinstance(v, Transformation)}

    if transformation_name is None:
        if 'main' in transformation_objects:
            dbg("Selected symbol 'main' from module as transformation.")
            return transformation_objects['main']
        else:
            name, instance = next((k, v) for k, v in transformation_objects.items())
            dbg(f"Selected symbol '{name}' from module as transformation.")
            return instance

    for instance in transformation_objects.values():
        if instance.name == transformation_name:
            dbg(f"Selected transformation named '{transformation_name}' from module "
                f"as transformation.")
            return instance

    dbg(f"Selected symbol '{transformation_name}' from module as transformation.")
    return transformation_objects[transformation_name]


def apply_transformation(transformation: Transformation, target: str) -> etree._ElementTree:
    document = etree.parse(target)
    copy_file(target, target + '.orig')
    dbg("Saved document backup with suffix '.orig'")
    dbg('Applying transformation.')
    root = transformation(document.getroot())
    document._setroot(root)
    return document


def write_file(document: etree._ElementTree, args: Namespace) -> None:
    document.write(args.target,
                   pretty_print=args.pretty,
                   # TODO obtain options from source:
                   encoding='utf-8',
                   xml_declaration=True)
    dbg('Wrote result back to file.')


def main(args: Sequence[str] = None) -> None:
    nfo('Starting')
    try:
        if args is None:
            args = sys.argv[1:]
        args = parse_args(args)
        setup_logging(args.verbose)
        dbg(f'Invoked with args: {args}')
        transformation = get_transformation(args.transformation)
        result = apply_transformation(transformation, args.target)
        write_file(result, args)
    except Exception:
        print_exc()
        raise SystemExit(2)


if __name__ == '__main__':
    main()


__all__ = [main.__name__]
