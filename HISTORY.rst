History
=======

0.2b1 (2019-06-23)
------------------

* refactored to base on delb_ instead of lxml
* *removed* from the available symbols for handler functions:
    - ``tree``
    - ``xpath_evaluator`` (use ``root.xpath`` instead)
* *renamed* available symbols for handler functions:
    - ``element`` -> ``node``
* *renamed* in core:
    - ``SkipToNextElement`` -> ``SkipToNextNode``
* *removed* from the lib:
    - ``drop_siblings``
    - ``extract_text``
    - ``has_tail``
    - ``init_elementmaker``
    - ``merge``
    - ``replace_text``
    - ``sub``
* *renamed* in the lib:
    - ``make_element`` -> ``make_node``
    - ``remove_element`` -> ``remove_node``
    - ``remove_elements`` -> ``remove_nodes``
    - ``sorter`` -> ``sort``
    - ``strip_attributes`` -> ``remove_attributes``
    - ``strip_namespace`` -> ``remove_namespace``

Various arguments to functions and methods have been renamed accordingly.

.. _delb: https://pypi.org/project/delb/


0.1b1 (2017-06-25)
------------------

* *new*: Allows the definition that any rule must match per transformation as
  ``common_rule_conditions``.
* Minor improvements and fixes.


0.1b0 (2017-06-19)
------------------

* First beta release.


0.1a0 (2017-05-02)
------------------

* First release on PyPI.
