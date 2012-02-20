"""Tests to ensure that the lxml tree builder generates good trees."""

import re

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
except ImportError, e:
    LXML_PRESENT = False

from bs4 import BeautifulSoup
from bs4.element import Comment, Doctype, SoupStrainer
from bs4.testing import skipIf
from bs4.tests import test_htmlparser
from bs4.testing import skipIf

@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing its tree builder.")
class TestLXMLTreeBuilder(test_htmlparser.TestHTMLParserTreeBuilder):
    """A smoke test for the LXML tree builder.

    Subclass this to test some other HTML tree builder. Subclasses of
    this test ensure that all of Beautiful Soup's tree builders
    generate more or less the same trees.

    It's okay for trees to differ--just override the appropriate test
    method to demonstrate how one tree builder differs from the LXML
    builder. But in general, all HTML tree builders should generate
    trees that make most of these tests pass.
    """

    def test_bare_string(self):
        # A bare string is turned into some kind of HTML document or
        # fragment recognizable as the original string.
        #
        # In this case, lxml puts a <p> tag around the bare string.
        self.assertSoupEquals(
            "A bare string", "<p>A bare string</p>")

    def test_cdata_where_its_ok(self):
        # lxml strips CDATA sections, no matter where they occur.
        markup = "<svg><![CDATA[foobar]]>"
        self.assertSoupEquals(markup, "<svg></svg>")

    def test_empty_element(self):
        # HTML's empty-element tags are recognized as such.
        self.assertSoupEquals(
            "<p>A <meta> tag</p>", "<p>A <meta/> tag</p>")

        self.assertSoupEquals(
            "<p>Foo<br/>bar</p>", "<p>Foo<br/>bar</p>")

    def test_naked_ampersands(self):
        # Ampersands are left alone.
        text = "<p>AT&T</p>"
        soup = self.soup(text)
        self.assertEqual(soup.p.string, "AT&T")

        # Even if they're in attribute values.
        invalid_url = '<a href="http://example.org?a=1&b=2;3">foo</a>'
        soup = self.soup(invalid_url)
        self.assertEqual(soup.a['href'], "http://example.org?a=1&b=2;3")

    def test_literal_in_textarea(self):
        # Anything inside a <textarea> is supposed to be treated as
        # the literal value of the field, (XXX citation
        # needed). html5lib does this correctly. But, lxml does its
        # best to parse the contents of a <textarea> as HTML.
        text = '<textarea>Junk like <b> tags and <&<&amp;</textarea>'
        soup = self.soup(text)
        self.assertEqual(len(soup.textarea.contents), 2)
        self.assertEqual(soup.textarea.contents[0], u"Junk like ")
        self.assertEqual(soup.textarea.contents[1].name, 'b')
        self.assertEqual(soup.textarea.b.string, u" tags and ")

    def test_literal_in_script(self):
        # The contents of a <script> tag are treated as a literal string,
        # even if that string contains HTML.
        javascript = 'if (i < 2) { alert("<b>foo</b>"); }'
        soup = self.soup('<script>%s</script>' % javascript)
        self.assertEqual(soup.script.string, javascript)

    def test_doctype(self):
        # Test a normal HTML doctype you'll commonly see in a real document.
        self._test_doctype(
            'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"')

    def test_namespaced_system_doctype(self):
        # Test a namespaced doctype with a system id.
        self._test_doctype('xsl:stylesheet SYSTEM "htmlent.dtd"')

    def test_namespaced_public_doctype(self):
        # Test a namespaced doctype with a public id.
        self._test_doctype('xsl:stylesheet PUBLIC "htmlent.dtd"')


@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing it on invalid markup.")
class TestLXMLTreeBuilderInvalidMarkup(
    test_htmlparser.TestHTMLParserTreeBuilderInvalidMarkup):

    def test_attribute_value_never_got_closed(self):
        markup = '<a href="http://foo.com/</a> and blah and blah'
        soup = self.soup(markup)
        self.assertEqual(
            soup.a['href'], "http://foo.com/</a> and blah and blah")

    def test_attribute_value_was_closed_by_subsequent_tag(self):
        markup = """<a href="foo</a>, </a><a href="bar">baz</a>"""
        soup = self.soup(markup)
        # The string between the first and second quotes was interpreted
        # as the value of the 'href' attribute.
        self.assertEqual(soup.a['href'], 'foo</a>, </a><a href=')

        #The string after the second quote (bar"), was treated as an
        #empty attribute called bar.
        self.assertEqual(soup.a['bar'], '')
        self.assertEqual(soup.a.string, "baz")

    def test_document_starts_with_bogus_declaration(self):
        soup = self.soup('<! Foo ><p>a</p>')
        # The declaration is ignored altogether.
        self.assertEqual(soup.encode(), b"<html><body><p>a</p></body></html>")

    def test_incomplete_declaration(self):
        # An incomplete declaration will screw up the rest of the document.
        self.assertSoupEquals('a<!b <p>c', '<p>a</p>')

    def test_nonsensical_declaration(self):
        # Declarations that don't make any sense are ignored.
        self.assertSoupEquals('<! Foo = -8><p>a</p>', "<p>a</p>")

    def test_unquoted_attribute_value(self):
        soup = self.soup('<a style={height:21px;}></a>')
        self.assertEqual(soup.a['style'], '{height:21px;}')

    def test_whitespace_in_doctype(self):
        # A declaration that has extra whitespace is ignored.
        self.assertSoupEquals(
            ('<! DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">'
             '<p>foo</p>'),
            '<p>foo</p>')

    def test_boolean_attribute_with_no_value_gets_empty_value(self):
        soup = self.soup("<table><td nowrap>foo</td></table>")
        self.assertEqual(soup.table.td['nowrap'], '')

    def test_cdata_where_it_doesnt_belong(self):
        #CDATA sections are ignored.
        markup = "<div><![CDATA[foo]]>"
        self.assertSoupEquals(markup, "<div></div>")

    def test_empty_element_tag_with_contents(self):
        self.assertSoupEquals("<br>foo</br>", "<br/>foo</br>")

    def test_nonexistent_entity(self):
        soup = self.soup("<p>foo&#bar;baz</p>")
        self.assertEqual(soup.p.string, "foobar;baz")

        # Compare a real entity.
        soup = self.soup("<p>foo&#100;baz</p>")
        self.assertEqual(soup.p.string, "foodbaz")

        # Also compare html5lib, which preserves the &# before the
        # entity name.

    def test_entity_was_not_finished(self):
        soup = self.soup("<p>&lt;Hello&gt")
        # Compare html5lib, which completes the entity.
        self.assertEqual(soup.p.string, "<Hello&gt")

    def test_fake_self_closing_tag(self):
        # If a self-closing tag presents as a normal tag, the 'open'
        # tag is treated as an instance of the self-closing tag and
        # the 'close' tag is ignored.
        self.assertSoupEquals(
            "<item><link>http://foo.com/</link></item>",
            "<item><link/>http://foo.com/</item>")

    def test_paragraphs_containing_block_display_elements(self):
        markup = self.soup("<p>this is the definition:"
                           "<dl><dt>first case</dt>")
        # The <p> tag is closed before the <dl> tag begins.
        self.assertEqual(markup.p.contents, ["this is the definition:"])

    def test_multiple_values_for_the_same_attribute(self):
        markup = '<b b="20" a="1" b="10" a="2" a="3" a="4"></b>'
        self.assertSoupEquals(markup, '<b a="1" b="20"></b>')


@skipIf(
    not LXML_PRESENT,
    "lxml seems not to be present, not testing it on encoding conversion.")
class TestLXMLParserTreeBuilderEncodingConversion(
    test_htmlparser.TestHTMLParserTreeBuilderEncodingConversion):
    # Re-run the lxml tests for HTMLParser
    pass
