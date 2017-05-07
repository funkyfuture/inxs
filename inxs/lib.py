from typing import Callable

from lxml import builder


def set_elementmaker(name: str = 'e', **kwargs):
    if 'namespace' in kwargs and 'nsmap' not in kwargs:
        kwargs['nsmap'] = {None: kwargs['namespace']}

    def wrapped(context):
        setattr(context, name, builder.ElementMaker(**kwargs))
    return wrapped


def sorter(object_name: str, key: Callable):
    def wrapped(transformation):
        return sorted(transformation._available_dependencies[object_name], key=key)
    return wrapped
