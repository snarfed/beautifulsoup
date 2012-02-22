"""Helper classes for tests."""

import copy
import functools
import unittest
from unittest import TestCase
from bs4 import BeautifulSoup
from bs4.element import (
    Comment,
    Doctype,
    SoupStrainer,
)

from bs4.builder import HTMLParserTreeBuilder
default_builder = HTMLParserTreeBuilder


class SoupTest(unittest.TestCase):

    @property
    def default_builder(self):
        return default_builder()

    def soup(self, markup, **kwargs):
        """Build a Beautiful Soup object from markup."""
        builder = kwargs.pop('builder', self.default_builder)
        return BeautifulSoup(markup, builder=builder, **kwargs)

    def document_for(self, markup):
        """Turn an HTML fragment into a document.

        The details depend on the builder.
        """
        return self.default_builder.test_fragment_to_document(markup)

    def assertSoupEquals(self, to_parse, compare_parsed_to=None):
        builder = self.default_builder
        obj = BeautifulSoup(to_parse, builder=builder)
        if compare_parsed_to is None:
            compare_parsed_to = to_parse

        self.assertEqual(obj.decode(), self.document_for(compare_parsed_to))


class HTMLTreeBuilderSmokeTest(object):

    """A basic test of a treebuilder's competence.

    Any HTML treebuilder, present or future, should be able to pass
    these tests. With invalid markup, there's room for interpretation,
    and different parsers can handle it differently. But with the
    markup in these tests, there's not much room for interpretation.
    """

    def assertDoctypeHandled(self, doctype_fragment):
        """Assert that a given doctype string is handled correctly."""
        doctype_str, soup = self._document_with_doctype(doctype_fragment)

        # Make sure a Doctype object was created.
        doctype = soup.contents[0]
        self.assertEqual(doctype.__class__, Doctype)
        self.assertEqual(doctype, doctype_fragment)
        self.assertEqual(str(soup)[:len(doctype_str)], doctype_str)

        # Make sure that the doctype was correctly associated with the
        # parse tree and that the rest of the document parsed.
        self.assertEqual(soup.p.contents[0], 'foo')

    def _document_with_doctype(self, doctype_fragment):
        """Generate and parse a document with the given doctype."""
        doctype = '<!DOCTYPE %s>' % doctype_fragment
        markup = doctype + '\n<p>foo</p>'
        soup = self.soup(markup)
        return doctype, soup

    def test_normal_doctypes(self):
        """Make sure normal, everyday HTML doctypes are handled correctly."""
        self.assertDoctypeHandled("html")
        self.assertDoctypeHandled(
            'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')

    def test_namespaced_system_doctype(self):
        # We can handle a namespaced doctype with a system ID.
        self.assertDoctypeHandled('xsl:stylesheet SYSTEM "htmlent.dtd"')

    def test_namespaced_public_doctype(self):
        # Test a namespaced doctype with a public id.
        self.assertDoctypeHandled('xsl:stylesheet PUBLIC "htmlent.dtd"')

    def test_deepcopy(self):
        """Make sure you can copy the tree builder.

        This is important because the builder is part of a
        BeautifulSoup object, and we want to be able to copy that.
        """
        copy.deepcopy(self.default_builder)

    def test_p_tag_is_never_empty_element(self):
        """A <p> tag is never designated as an empty-element tag.

        Even if the markup shows it as an empty-element tag, it
        shouldn't be presented that way.
        """
        soup = self.soup("<p/>")
        self.assertFalse(soup.p.is_empty_element)
        self.assertEqual(str(soup.p), "<p></p>")

    def test_br_is_always_empty_element_tag(self):
        """A <br> tag is designated as an empty-element tag.

        Some parsers treat <br></br> as one <br/> tag, some parsers as
        two tags, but it should always be an empty-element tag.
        """
        soup = self.soup("<br></br>")
        self.assertTrue(soup.br.is_empty_element)
        self.assertEqual(str(soup.br), "<br/>")

    def test_comment(self):
        # Comments are represented as Comment objects.
        markup = "<p>foo<!--foobar-->baz</p>"
        self.assertSoupEquals(markup)

        soup = self.soup(markup)
        comment = soup.find(text="foobar")
        self.assertEqual(comment.__class__, Comment)

    def test_preserved_whitespace_in_pre_and_textarea(self):
        """Whitespace must be preserved in <pre> and <textarea> tags."""
        self.assertSoupEquals("<pre>   </pre>")
        self.assertSoupEquals("<textarea> woo  </textarea>")

    def test_nested_inline_elements(self):
        """Inline elements can be nested indefinitely."""
        b_tag = "<b>Inside a B tag</b>"
        self.assertSoupEquals(b_tag)

        nested_b_tag = "<p>A <i>nested <b>tag</b></i></p>"
        self.assertSoupEquals(nested_b_tag)

        double_nested_b_tag = "<p>A <a>doubly <i>nested <b>tag</b></i></a></p>"
        self.assertSoupEquals(nested_b_tag)

    def test_nested_block_level_elements(self):
        """Block elements can be nested."""
        soup = self.soup('<blockquote><p><b>Foo</b></p></blockquote>')
        blockquote = soup.blockquote
        self.assertEqual(blockquote.p.b.string, 'Foo')
        self.assertEqual(blockquote.b.string, 'Foo')

    def test_correctly_nested_tables(self):
        """One table can go inside another one."""
        markup = ('<table id="1">'
                  '<tr>'
                  "<td>Here's another table:"
                  '<table id="2">'
                  '<tr><td>foo</td></tr>'
                  '</table></td>')

        self.assertSoupEquals(
            markup,
            '<table id="1"><tr><td>Here\'s another table:'
            '<table id="2"><tr><td>foo</td></tr></table>'
            '</td></tr></table>')

        self.assertSoupEquals(
            "<table><thead><tr><td>Foo</td></tr></thead>"
            "<tbody><tr><td>Bar</td></tr></tbody>"
            "<tfoot><tr><td>Baz</td></tr></tfoot></table>")

    def test_hex_entities_in_text(self):
        """This mainly tests a BS workaround for a bug in HTMLParser."""
        self.assertSoupEquals("<p>&#xf1;</p>", u"<p>\xf1</p>")

    #
    # Generally speaking, tests below this point are more tests of
    # Beautiful Soup than tests of the tree builders. But parsers are
    # weird, so we run these tests separately for every tree builder
    # to detect any differences.
    #

    def test_soupstrainer(self):
        """Parsers should be able to work with SoupStrainers."""
        strainer = SoupStrainer("b")
        soup = self.soup("A <b>bold</b> <meta/> <i>statement</i>",
                         parse_only=strainer)
        self.assertEqual(soup.decode(), "<b>bold</b>")

    def test_single_quote_attribute_values_become_double_quotes(self):
        self.assertSoupEquals("<foo attr='bar'></foo>",
                              '<foo attr="bar"></foo>')

    def test_attribute_values_with_nested_quotes_are_left_alone(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        self.assertSoupEquals(text)

    def test_attribute_values_with_double_nested_quotes_get_quoted(self):
        text = """<foo attr='bar "brawls" happen'>a</foo>"""
        soup = self.soup(text)
        soup.foo['attr'] = 'Brawls happen at "Bob\'s Bar"'
        self.assertSoupEquals(
            soup.foo.decode(),
            """<foo attr="Brawls happen at &quot;Bob\'s Bar&quot;">a</foo>""")

    def test_ampersand_in_attribute_value_gets_quoted(self):
        self.assertSoupEquals('<this is="really messed up & stuff"></this>',
                              '<this is="really messed up &amp; stuff"></this>')

    def test_entities_in_strings_converted_during_parsing(self):
        # Both XML and HTML entities are converted to Unicode characters
        # during parsing.
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>"
        self.assertSoupEquals(text, expected)

    def test_smart_quotes_converted_on_the_way_in(self):
        # Microsoft smart quotes are converted to Unicode characters during
        # parsing.
        quote = b"<p>\x91Foo\x92</p>"
        soup = self.soup(quote)
        self.assertEqual(
            soup.p.string,
            u"\N{LEFT SINGLE QUOTATION MARK}Foo\N{RIGHT SINGLE QUOTATION MARK}")

    def test_non_breaking_spaces_converted_on_the_way_in(self):
        soup = self.soup("<a>&nbsp;&nbsp;</a>")
        self.assertEqual(soup.a.string, u"\N{NO-BREAK SPACE}" * 2)

    def test_entities_converted_on_the_way_out(self):
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"<p>&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;</p>".encode("utf-8")
        soup = self.soup(text)
        self.assertEqual(soup.p.encode("utf-8"), expected)

    def test_real_iso_latin_document(self):
        # Smoke test of interrelated functionality, using an
        # easy-to-understand document.

        # Here it is in Unicode. Note that it claims to be in ISO-Latin-1.
        unicode_html = u'<html><head><meta content="text/html; charset=ISO-Latin-1" http-equiv="Content-type"/></head><body><p>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</p></body></html>'

        # That's because we're going to encode it into ISO-Latin-1, and use
        # that to test.
        iso_latin_html = unicode_html.encode("iso-8859-1")

        # Parse the ISO-Latin-1 HTML.
        soup = self.soup(iso_latin_html)
        # Encode it to UTF-8.
        result = soup.encode("utf-8")

        # What do we expect the result to look like? Well, it would
        # look like unicode_html, except that the META tag would say
        # UTF-8 instead of ISO-Latin-1.
        expected = unicode_html.replace("ISO-Latin-1", "utf-8")

        # And, of course, it would be in UTF-8, not Unicode.
        expected = expected.encode("utf-8")

        # Ta-da!
        self.assertEqual(result, expected)

    def test_real_shift_jis_document(self):
        # Smoke test to make sure the parser can handle a document in
        # Shift-JIS encoding, without choking.
        shift_jis_html = (
            b'<html><head></head><body><pre>'
            b'\x82\xb1\x82\xea\x82\xcdShift-JIS\x82\xc5\x83R\x81[\x83f'
            b'\x83B\x83\x93\x83O\x82\xb3\x82\xea\x82\xbd\x93\xfa\x96{\x8c'
            b'\xea\x82\xcc\x83t\x83@\x83C\x83\x8b\x82\xc5\x82\xb7\x81B'
            b'</pre></body></html>')
        unicode_html = shift_jis_html.decode("shift-jis")
        soup = self.soup(unicode_html)

        # Make sure the parse tree is correctly encoded to various
        # encodings.
        self.assertEqual(soup.encode("utf-8"), unicode_html.encode("utf-8"))
        self.assertEqual(soup.encode("euc_jp"), unicode_html.encode("euc_jp"))

    def test_real_hebrew_document(self):
        # A real-world test to make sure we can convert ISO-8859-9 (a
        # Hebrew encoding) to UTF-8.
        hebrew_document = b'<html><head><title>Hebrew (ISO 8859-8) in Visual Directionality</title></head><body><h1>Hebrew (ISO 8859-8) in Visual Directionality</h1>\xed\xe5\xec\xf9</body></html>'
        soup = self.soup(
            hebrew_document, from_encoding="iso8859-8")
        self.assertEqual(soup.original_encoding, 'iso8859-8')
        self.assertEqual(
            soup.encode('utf-8'),
            hebrew_document.decode("iso8859-8").encode("utf-8"))

    def test_meta_tag_reflects_current_encoding(self):
        # Here's the <meta> tag saying that a document is
        # encoded in Shift-JIS.
        meta_tag = ('<meta content="text/html; charset=x-sjis" '
                    'http-equiv="Content-type"/>')

        # Here's a document incorporating that meta tag.
        shift_jis_html = (
            '<html><head>\n%s\n'
            '<meta http-equiv="Content-language" content="ja"/>'
            '</head><body>Shift-JIS markup goes here.') % meta_tag
        soup = self.soup(shift_jis_html)

        # Parse the document, and the charset is replaced with a
        # generic value.
        parsed_meta = soup.find('meta', {'http-equiv': 'Content-type'})
        self.assertEqual(parsed_meta['content'],
                          'text/html; charset=%SOUP-ENCODING%')
        self.assertEqual(parsed_meta.contains_substitutions, True)

        # For the rest of the story, see TestSubstitutions in
        # test_tree.py.


def skipIf(condition, reason):
   def nothing(test, *args, **kwargs):
       return None

   def decorator(test_item):
       if condition:
           return nothing
       else:
           return test_item

   return decorator
