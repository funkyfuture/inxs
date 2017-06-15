from lxml import builder, etree


from inxs import lib, Rule, Transformation


def test_strip_namespace():
    namespace = 'http://www.example.org/ns/'
    e = builder.ElementMaker(namespace=namespace, nsmap={'x': namespace})
    root = e.div()
    t = Transformation(
        Rule(namespace, lib.strip_namespace)
    )
    result = t(root)
    assert result.tag == 'div'
