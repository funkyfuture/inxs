from pathlib import Path

from inxs.cli import main as _main

from tests import equal_documents


def main(*args):
    _args = ()
    for arg in args:
        if isinstance(arg, Path):
            _args += (str(arg),)
        else:
            _args += (arg,)
    _main(_args)


# TODO case-study with this use-case
def test_mods_to_tei(datadir):
    main("--inplace", datadir / "mods_to_tei.py", datadir / "mods_to_tei.xml")
    assert equal_documents(datadir / "mods_to_tei.xml", datadir / "mods_to_tei_exp.xml")
