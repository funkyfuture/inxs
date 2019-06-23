import operator as op

from delb import first, new_tag_node, TagNode, tag

from inxs import lib, If, Once, Ref, Rule, Transformation

MODS_NAMESPACE = "http://www.loc.gov/mods/v3"
TEI_NAMESPACE = "http://www.tei-c.org/ns/1.0"


as_result = lib.put_variable("result")
f = lib.f
prev = Ref("previous_result")
result = Ref("result")


def generate_skeleton(context):
    header = context.result = new_tag_node("teiHeader", namespace=TEI_NAMESPACE)

    context.biblFull_titleStmt = header.new_tag_node("titleStmt")
    context.msDesc = header.new_tag_node("msDesc")
    context.publicationStmt = header.new_tag_node("publicationStmt")
    context.titleStmt = header.new_tag_node("titleStmt")

    header.append_child(
        tag(
            "fileDesc",
            (
                tag(
                    "sourceDesc",
                    (
                        # TODO? tei.bibl(),
                        tag(
                            "biblFull",
                            (context.publicationStmt, context.biblFull_titleStmt),
                        ),
                        context.msDesc,
                    ),
                ),
                context.titleStmt,
            ),
        ),
        tag("encodingDesc"),
        tag("profileDesc"),
    )


def get_title(node: TagNode, titleStmt: TagNode, biblFull_titleStmt: TagNode):
    non_sort = first(node.css_select("mods|nonSort"))
    main_title = (non_sort.full_text + " ") if non_sort is not None else ""
    main_title += first(node.css_select("mods|title")).full_text
    sub_title = first(node.css_select("mods|subTitle")).full_text

    for target in (titleStmt, biblFull_titleStmt):
        target.append_child(
            tag("title", {"type": "main"}, main_title),
            tag("title", {"type": "sub"}, sub_title),
        )


def get_publication(node: TagNode, publicationStmt: TagNode):
    date = first(node.css_select("mods|dateIssued")).full_text
    name = first(node.css_select("mods|publisher")).full_text
    place = first(node.xpath('./mods:place/mods:placeTerm[@type="text"]')).full_text

    publicationStmt.append_child(
        tag("publisher", tag("name", name)),
        tag("pubPlace", place),
        tag("date", {"type": "creation"}, date),
    )


mods_name = Transformation(
    Once(
        ("roleTerm", {"type": "text"}, lib.text_equals("author")),
        (
            lib.make_node(local_name="author", namespace=TEI_NAMESPACE),
            as_result,
            lib.put_variable("role", "author"),
        ),
    ),
    Once(
        ("namePart", {"type": "family"}),
        (lib.get_text, lib.f(tag, "surname", prev), lib.append("result")),
    ),
    Once(
        ("namePart", {"type": "given"}),
        (lib.get_text, lib.f(tag, "forename", prev), lib.append("result")),
    ),
    Once(
        If(Ref("role"), op.eq, "author"),
        (
            lib.append("outer_context.titleStmt", Ref("result"), copy_node=True),
            lib.append(
                "outer_context.biblFull_titleStmt", Ref("result"), copy_node=True
            ),
        ),
    ),
    common_rule_conditions=MODS_NAMESPACE,
    copy=False,
    result_object=None,
)

mods_location = Transformation(
    f(new_tag_node, "msIdentifier", namespace=TEI_NAMESPACE),
    as_result,
    Rule(
        "physicalLocation",
        (
            lib.get_text,
            f(str.strip, prev),
            lib.f(tag, "repository", prev),
            lib.append("result"),
        ),
    ),
    Rule(
        "shelfLocator",
        (
            lib.get_text,
            f(str.strip, prev),
            lib.f(tag, "idno", {"type": "shelfmark"}, prev),
            lib.append("result"),
        ),
    ),
    common_rule_conditions=MODS_NAMESPACE,
    copy=False,
    result_object="context.result",
)

from_mods = Transformation(
    generate_skeleton,
    Rule("titleInfo", get_title),
    Rule("name", f(mods_name, Ref("node"), outer_context=Ref("context"))),
    Rule("originInfo", get_publication),
    Rule("location", (f(mods_location, Ref("node")), lib.append("msDesc"))),
    common_rule_conditions=MODS_NAMESPACE,
    result_object="context.result",
)

main = Transformation(
    Once((MODS_NAMESPACE, "mods"), (f(from_mods, Ref("node"), copy=True), as_result)),
    result_object="context.result",
)
