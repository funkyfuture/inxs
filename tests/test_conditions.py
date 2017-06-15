from lxml import etree

from inxs import *


def test_grouped_steps():
    def append_to_list(value):
        def appender(list):
            list.append(value)
        return appender

    stpgrp_c = (append_to_list(3), append_to_list(4))
    stpgrp_a = (append_to_list(1))
    stpgrp_b = (append_to_list(2), stpgrp_c, append_to_list(5))

    transformation = Transformation(
        append_to_list(0),
        stpgrp_a,
        stpgrp_b,
        context={'list': []}, result_object='context.list'
    )
    result = transformation(etree.Element('root'))
    for exp, val in enumerate(result):
        assert exp == val
