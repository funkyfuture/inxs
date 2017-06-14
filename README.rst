inxs – A framework for XML transformations without boilerplate.
===============================================================

inxs is inexcessive.

inxs is not XSLT.

inxs is ISC-licensed.

inxs is fully documented here: https://inxs.readthedocs.io.


At a glimpse
------------

`Wikipedia XSLT example #1`_:

.. list-table::
   :header-rows: 1

   * - **inxs**
     - **XSLT**
   * - .. code-block:: python

          def extract_person(element):
              return element.attrib['username'], element.find('name').text

          def append_person(previous_result, target):
              element = etree.SubElement(target, 'name', {'username': previous_result[0]})
              element.text = previous_result[1]
              return element

          transformation = Transformation(
              Rule('person', (extract_person, append_person)),
              result_object='context.target', context={'target': etree.Element('root')})

     - .. code-block:: xslt

          <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
            <xsl:output method="xml" indent="yes"/>

             <xsl:template match="/persons">
               <root>
                 <xsl:apply-templates select="person"/>
               </root>
             </xsl:template>

             <xsl:template match="person">
               <name username="{@username}">
                 <xsl:value-of select="name" />
               </name>
             </xsl:template>

          </xsl:stylesheet>


`Wikipedia XSLT example #2`_:

.. list-table::
   :header-rows: 1

   * - **inxs**
     - **XSLT**
   * - .. code-block:: python


          def generate_skeleton(context, e):
              context.html = e.html(
                  e.head(e.title('Testing XML Example')),
                  e.body(e.h1('Persons'), e.ul()))
              context.persons_list = context.html.xpath('./body/ul', smart_prefix=True)[0]

          def extract_person(element, persons):
              persons.append((element.find('name').text, element.find('family-name').text))

          def list_persons(previous_result, persons_list, e):
              persons_list.extend(e.li(f'{x[1]}, {x[0]}') for x in previous_result)

          transformation = Transformation(
              lib.add_elementmaker(namespace='http://www.w3.org/1999/xhtml'),
              generate_skeleton,
              Rule('person', extract_person),
              lib.sorter('persons', itemgetter(1)),
              list_persons,
              result_object='context.html', context={'persons': []})

     - .. code-block:: xslt

          <xsl:stylesheet version="1.0"
            xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
            xmlns="http://www.w3.org/1999/xhtml">

            <xsl:output method="xml" indent="yes" encoding="UTF-8"/>

            <xsl:template match="/persons">
             <html>
               <head> <title>Testing XML Example</title> </head>
               <body>
                 <h1>Persons</h1>
                 <ul>
                   <xsl:apply-templates select="person">
                     <xsl:sort select="family-name" />
                   </xsl:apply-templates>
                 </ul>
               </body>
             </html>
            </xsl:template>

            <xsl:template match="person">
             <li>
               <xsl:value-of select="family-name"/> (…) <xsl:value-of select="name"/>
             </li>
            </xsl:template>

         </xsl:stylesheet>


`Here`_ you can find the source repository and issue tracker of inxs.

.. _here: https://github.com/funkyfuture/inxs
.. _Wikipedia XSLT example #1: https://en.wikipedia.org/wiki/XSLT#Example_1_.28transforming_XML_to_XML.29
.. _Wikipedia XSLT example #2: https://en.wikipedia.org/wiki/XSLT#Example_2_.28transforming_XML_to_XHTML.29


Roadmap
-------

0.1b0
.....

- enough documentation to get someone started

0.1
...

- reasonable test coverage
- some usages in the wild / feedback thereof


Ideas
-----

- a config option to define aliases for the available handler dependencies
