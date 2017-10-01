# TODO error handling
# TODO documentation
# TODO tests
# TODO allow passing arguments


from argparse import ArgumentParser
from traceback import print_exc
import importlib.util
import logging
from pathlib import Path
from shutil import copy2 as copy_file
import sys

from lxml import etree

from inxs import Transformation
from inxs.lib import dbg, logger, nfo


def parse_args():
    parser = ArgumentParser()

    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('transformation')
    parser.add_argument('target')

    return parser.parse_args()


def setup_logging(verbosity: int):
    level = ('WARNING', 'INFO', 'DEBUG')[verbosity]
    console_log_handler = logging.StreamHandler(sys.stdout)
    console_log_handler.setLevel(level)
    logger.addHandler(console_log_handler)
    logger.setLevel(level)


def get_transformation(location: str):
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


def apply_transformation(transformation: Transformation, target: str):
    document = etree.parse(target)
    copy_file(target, target + '.orig')
    dbg("Saved document backup with suffix '.orig'")
    dbg('Applying transformation.')
    root = transformation(document.getroot())
    document._setroot(root)
    document.write(target,
                   encoding='utf-8',  # TODO obtain options from source
                   xml_declaration=True)
    dbg('Wrote result back to file.')


def main():
    nfo('Starting')
    try:
        args = parse_args()
        setup_logging(args.verbose)
        dbg(f'Invoked with args: {args}')
        transformation = get_transformation(args.transformation)
        apply_transformation(transformation, args.target)
    except Exception as e:
        print_exc(e)
        raise SystemExit(2)


if __name__ == '__main__':
    main()


__all__ = []
