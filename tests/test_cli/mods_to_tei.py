import operator as op

from inxs import lib, AbortRule, If, Once, Ref, Rule, Transformation
from inxs.lxml_utils import find
from lxml import builder, etree  # noqa


METS_NAMESPACE = 'http://www.loc.gov/METS/'
MODS_NAMESPACE = 'http://www.loc.gov/mods/v3'
TEI_NAMESPACE = 'http://www.tei-c.org/ns/1.0'

NAMESPACE_MAP = {
    'mets': METS_NAMESPACE,
    'mods': MODS_NAMESPACE,
    'tei': TEI_NAMESPACE
}


as_result = lib.put_variable('result')
f = lib.f
prev = Ref('previous_result')
result = Ref('result')
tei = builder.ElementMaker(namespace=TEI_NAMESPACE,
                           nsmap={None: TEI_NAMESPACE})


def generate_skeleton(context):
    context.biblFull_titleStmt = tei.titleStmt()
    context.msDesc = tei.msDesc()
    context.publicationStmt = tei.publicationStmt()
    context.titleStmt = tei.titleStmt()

    context.result = tei.teiHeader(
        tei.fileDesc(
            tei.sourceDesc(
                # TODO? tei.bibl(),
                tei.biblFull(
                    context.publicationStmt,
                    context.biblFull_titleStmt
                ),
                context.msDesc,
            ),
            context.titleStmt
        ),
        tei.encodingDesc(),
        tei.profileDesc()
    )


def get_title(element, titleStmt, biblFull_titleStmt):
    non_sort = find(element, 'mods:nonSort')
    main_title = (non_sort.text + ' ') if non_sort is not None else ''
    main_title += find(element, 'mods:title').text
    sub_title = find(element, 'mods:subTitle').text

    for target in (titleStmt, biblFull_titleStmt):
        target.extend((
            tei.title(main_title, type='main'),
            tei.title(sub_title, type='sub')
        ))


def get_publication(element, publicationStmt):
    place = element.xpath('./mods:place/mods:placeTerm[@type="text"]',
                          smart_prefix=True)[0].text
    publicationStmt.extend((
        tei.publisher(
            tei.name(find(element, 'mods:publisher').text)),
        tei.pubPlace(place),
        tei.date(find(element, 'mods:dateIssued').text, type='creation'))
    )


mods_name = Transformation(
    Once(('roleTerm', {'type': 'text'}, lib.text_equals('author')),
         (lib.make_element('author', TEI_NAMESPACE), as_result,
          lib.put_variable('role', 'author'))),

    Once(('namePart', {'type': 'family'}),
         (lib.get_text, lib.sub(result, 'surname', text=prev))),
    Once(('namePart', {'type': 'given'}),
         (lib.get_text, lib.sub(result, 'forename', text=prev))),

    Once(If(Ref('role'), op.eq, 'author'),
         (lib.get_variable('result'),
          lib.append('outer_context.titleStmt'),
          lib.append('outer_context.biblFull_titleStmt'))),

    common_rule_conditions=MODS_NAMESPACE,
    copy=False, result_object=None
)


mods_location = Transformation(
    f(etree.Element, 'msIdentifier', nsmap={None: TEI_NAMESPACE}),
    as_result,

    Rule('physicalLocation',
         (lib.get_text, f(str.strip, prev),
          lib.sub(result, 'repository', text=prev))),
    Rule('shelfLocator',
         (lib.get_text, f(str.strip, prev),
          lib.sub(result, 'idno', text=prev, type='shelfmark'))),

    common_rule_conditions=MODS_NAMESPACE,
    copy=False, result_object='context.result'
)


from_mods = Transformation(
    generate_skeleton,

    Rule('titleInfo', get_title),
    Rule('name',
         f(mods_name, Ref('element'), outer_context=Ref('context'))),
    Rule('originInfo', get_publication),
    Rule('location',
         (f(mods_location, Ref('element')), lib.append('msDesc'))),

    common_rule_conditions=MODS_NAMESPACE,
    result_object='context.result'
)


main = Transformation(
    Rule((MODS_NAMESPACE, 'mods'),
         (f(from_mods, Ref('root'), copy=True), as_result,
          AbortRule)),
    result_object='context.result'
)
