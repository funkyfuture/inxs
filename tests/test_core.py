import operator
import re
from types import SimpleNamespace

from delb import Document, TagNode
from pytest import mark, raises

from inxs import (
    __version__,
    AbortRule,
    AbortTransformation,
    If,
    Not,
    Ref,
    Rule,
    SkipToNextNode,
    Transformation,
)
from inxs import lib


def test_aborts():
    def put_foo(context):
        context.foo = "foo"

    transformation = Transformation(
        AbortTransformation, put_foo, result_object="context"
    )
    result = transformation(Document("<root/>"))
    assert getattr(result, "foo", None) is None


def test_config_is_immutable():
    trnsfmtn = Transformation(
        lib.put_variable("test", "result"),
        name="strip_surrounding_content",
        result_object="context.test",
    )
    document = Document("<root/>")

    assert trnsfmtn(document) == "result"
    assert trnsfmtn(document) == "result"


def test_dotted_Ref():
    transformation = SimpleNamespace(
        _available_symbols={"root": SimpleNamespace(item="check")}
    )
    assert Ref("root.item")(transformation) == "check"


def test_grouped_steps():
    def append_to_list(value):
        def appender(list):
            list.append(value)

        return appender

    stpgrp_c = (append_to_list(3), append_to_list(4))
    stpgrp_b = (append_to_list(2), stpgrp_c, append_to_list(5))
    stpgrp_a = append_to_list(1)

    transformation = Transformation(
        append_to_list(0),
        stpgrp_a,
        stpgrp_b,
        context={"list": []},
        result_object="context.list",
    )
    result = transformation(Document("<root/>"))
    for exp, val in enumerate(result):
        assert exp == val


def test_invalid_input_raises_type_error():
    transformation = Transformation()
    with raises(TypeError):
        transformation({})


def test_SkipToNextElement():
    def more_complicated_test(node: TagNode):
        # well, supposedly
        if "x" not in node.attributes:
            raise SkipToNextNode
        if int(node.attributes["x"]) % 2:
            raise SkipToNextNode
        return node.local_name

    transformation = Transformation(
        Rule("*", (more_complicated_test, lib.append("evens"))),
        context={"evens": []},
        result_object="context.evens",
    )
    doc = Document('<root><a x="1"/><b x="2"/><c x="3"/><d x="4"/></root>')
    assert transformation(doc) == ["b", "d"]


def test_subtransformation():
    subtransformation = Transformation(Rule("*", lib.set_localname("pablo")))
    transformation = Transformation(
        lib.f(id, Ref("root")),
        lib.put_variable("source_id"),
        subtransformation,
        lib.f(id, Ref("root")),
        lib.put_variable("result_id"),
        lib.debug_symbols("source_id", "result_id"),
        Rule(
            Not(If(Ref("source_id"), operator.eq, Ref("result_id"))),
            (
                lib.debug_message("NO!"),
                lib.debug_symbols("root"),
                lib.set_localname("neruda"),
                AbortRule,
            ),
        ),
    )
    doc = Document("<augustus />")
    assert doc.root.local_name == "augustus"

    result = transformation(doc)
    assert result.root.local_name == "pablo"


version_pattern = re.compile(r"\d+\.\d+(\.\d+)?((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?")


@mark.parametrize("s", ("0.1", "0.1b2.dev3", "0.1b2", "1.0", "1.0.1", __version__))
def test_version(s):
    assert version_pattern.match(s)
