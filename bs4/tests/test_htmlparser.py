import copy
from HTMLParser import HTMLParseError
from bs4.element import Comment, Doctype, SoupStrainer
from bs4.builder import HTMLParserTreeBuilder
from bs4.element import CData
from bs4.testing import SoupTest

class TestHTMLParserTreeBuilder(SoupTest):

    """A smoke test for the built-in tree builder.

    Subclass this to test some other HTML tree builder. Subclasses of
    this test ensure that all of Beautiful Soup's tree builders
    generate more or less the same trees.

    It's okay for trees to differ--just override the appropriate test
    method to demonstrate how one tree builder differs from the
    default builder. But in general, all HTML tree builders should
    generate trees that make most of these tests pass.
    """

    @property
    def default_builder(self):
        return HTMLParserTreeBuilder()

    def test_bare_string(self):
        # A bare string is turned into some kind of HTML document or
        # fragment recognizable as the original string.
        #
        # HTMLParser does not modify the bare string at all.
        self.assertSoupEquals("A bare string")

    def test_cdata_where_its_ok(self):
        # HTMLParser recognizes CDATA sections and passes them through.
        markup = "<svg><![CDATA[foobar]]></svg>"
        self.assertSoupEquals(markup)
        soup = self.soup(markup)
        string = soup.svg.string
        self.assertEqual(string, "foobar")
        self.assertTrue(isinstance(string, CData))

    def test_hex_entities_in_text(self):
        # XXX This tests a workaround for a bug in HTMLParser.
        self.assertSoupEquals("<p>&#xf1;</p>", u"<p>\xf1</p>")

    def test_entities_in_attribute_values_converted_during_parsing(self):

        # The numeric entity isn't recognized without the closing
        # semicolon.
        text = '<x t="pi&#241ata">'
        expected = u"pi\N{LATIN SMALL LETTER N WITH TILDE}ata"
        soup = self.soup(text)
        self.assertEqual(soup.x['t'], "pi&#241ata")

        text = '<x t="pi&#241;ata">'
        expected = u"pi\N{LATIN SMALL LETTER N WITH TILDE}ata"
        soup = self.soup(text)
        self.assertEqual(soup.x['t'], u"pi\xf1ata")

        text = '<x t="pi&#xf1;ata">'
        soup = self.soup(text)
        self.assertEqual(soup.x['t'], expected)

        text = '<x t="sacr&eacute; bleu">'
        soup = self.soup(text)
        self.assertEqual(
            soup.x['t'],
            u"sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu")

        # This can cause valid HTML to become invalid.
        valid_url = '<a href="http://example.org?a=1&amp;b=2;3">foo</a>'
        soup = self.soup(valid_url)
        self.assertEqual(soup.a['href'], "http://example.org?a=1&b=2;3")

    # I think it would be very difficult to 'fix' these tests, judging
    # from my experience with previous versions of Beautiful Soup.
    def test_naked_ampersands(self):
        # Ampersands are treated as entities.
        text = "<p>AT&T</p>"
        soup = self.soup(text)
        self.assertEqual(soup.p.string, "AT&T;")

    def test_literal_in_textarea(self):
        # Anything inside a <textarea> is supposed to be treated as
        # the literal value of the field, (XXX citation
        # needed). html5lib does this correctly. But, HTMLParser does its
        # best to parse the contents of a <textarea> as HTML.
        text = '<textarea>Junk like <b> tags and <&<&amp;</textarea>'
        soup = self.soup(text)
        self.assertEqual(len(soup.textarea.contents), 2)
        self.assertEqual(soup.textarea.contents[0], u"Junk like ")
        self.assertEqual(soup.textarea.contents[1].name, 'b')
        self.assertEqual(soup.textarea.b.string, u" tags and <&<&")

    def test_literal_in_script(self):
        # Some versions of HTMLParser choke on markup like this:
        #  if (i < 2) { alert("<b>foo</b>"); }
        # Some versions of HTMLParser don't.
        #
        # The easiest thing is to just not run this test for HTMLParser.
        pass

    # Namespaced doctypes cause an HTMLParseError
    def test_namespaced_system_doctype(self):
        self.assertRaises(HTMLParseError, self._test_doctype,
                          'xsl:stylesheet SYSTEM "htmlent.dtd"')

    def test_namespaced_public_doctype(self):
        self.assertRaises(HTMLParseError, self._test_doctype,
                          'xsl:stylesheet PUBLIC "htmlent.dtd"')

    def _test_doctype(self, doctype_fragment):
        """Run a battery of assertions on a given doctype string.

        HTMLParser doesn't actually behave like this, so this method
        is never called in this class. But many other builders do
        behave like this, so I've put the method in the superclass.
        """
        doctype_str = '<!DOCTYPE %s>' % doctype_fragment
        markup = doctype_str + '<p>foo</p>'
        soup = self.soup(markup)
        doctype = soup.contents[0]
        self.assertEqual(doctype.__class__, Doctype)
        self.assertEqual(doctype, doctype_fragment)
        self.assertEqual(str(soup)[:len(doctype_str)], doctype_str)

        # Make sure that the doctype was correctly associated with the
        # parse tree and that the rest of the document parsed.
        self.assertEqual(soup.p.contents[0], 'foo')

# -------------------------

    def test_mixed_case_tags(self):
        # Mixed-case tags are folded to lowercase.
        self.assertSoupEquals(
            "<a><B><Cd><EFG></efg></CD></b></A>",
            "<a><b><cd><efg></efg></cd></b></a>")


    def test_empty_tag_thats_not_an_empty_element_tag(self):
        # A tag that is empty but not an HTML empty-element tag
        # is not presented as an empty-element tag.
        self.assertSoupEquals("<p>", "<p></p>")

    def test_comment(self):
        # Comments are represented as Comment objects.
        markup = "<p>foo<!--foobar-->baz</p>"
        self.assertSoupEquals(markup)

        soup = self.soup(markup)
        comment = soup.find(text="foobar")
        self.assertEqual(comment.__class__, Comment)

    def test_nested_inline_elements(self):
        # Inline tags can be nested indefinitely.
        b_tag = "<b>Inside a B tag</b>"
        self.assertSoupEquals(b_tag)

        nested_b_tag = "<p>A <i>nested <b>tag</b></i></p>"
        self.assertSoupEquals(nested_b_tag)

        double_nested_b_tag = "<p>A <a>doubly <i>nested <b>tag</b></i></a></p>"
        self.assertSoupEquals(nested_b_tag)

    def test_nested_block_level_elements(self):
        soup = self.soup('<blockquote><p><b>Foo</b></p></blockquote>')
        blockquote = soup.blockquote
        self.assertEqual(blockquote.p.b.string, 'Foo')
        self.assertEqual(blockquote.b.string, 'Foo')

    # This is a <table> tag containing another <table> tag in one of its
    # cells.
    TABLE_MARKUP_1 = ('<table id="1">'
                     '<tr>'
                     "<td>Here's another table:"
                     '<table id="2">'
                     '<tr><td>foo</td></tr>'
                     '</table></td>')

    def test_correctly_nested_tables(self):
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

    def test_collapsed_whitespace(self):
        """In most tags, whitespace is collapsed."""
        self.assertSoupEquals("<p>   </p>", "<p> </p>")

    def test_preserved_whitespace_in_pre_and_textarea(self):
        """In <pre> and <textarea> tags, whitespace is preserved."""
        self.assertSoupEquals("<pre>   </pre>")
        self.assertSoupEquals("<textarea> woo  </textarea>")

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

    # Tests below this line need work.

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

    def test_entities_converted_on_the_way_out(self):
        text = "<p>&lt;&lt;sacr&eacute;&#32;bleu!&gt;&gt;</p>"
        expected = u"&lt;&lt;sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!&gt;&gt;".encode("utf-8")
        soup = self.soup(text)
        str = soup.p.string
        #self.assertEqual(str.encode("utf-8"), expected)

    def test_br_tag_is_empty_element(self):
        """A <br> tag is designated as an empty-element tag."""
        soup = self.soup("<br></br>")
        self.assertTrue(soup.br.is_empty_element)
        self.assertEqual(str(soup.br), "<br/>")

    def test_p_tag_is_not_empty_element(self):
        """A <p> tag is not designated as an empty-element tag."""
        soup = self.soup("<p/>")
        self.assertFalse(soup.p.is_empty_element)
        self.assertEqual(str(soup.p), "<p></p>")

    def test_soupstrainer(self):
        strainer = SoupStrainer("b")
        soup = self.soup("A <b>bold</b> <meta/> <i>statement</i>",
                         parse_only=strainer)
        self.assertEqual(soup.decode(), "<b>bold</b>")

    def test_deepcopy(self):
        # Make sure you can copy the builder. This is important because
        # the builder is part of a BeautifulSoup object, and we want to be
        # able to copy that.
        copy.deepcopy(self.default_builder)

class TestHTMLParserTreeBuilderInvalidMarkup(SoupTest):
    """Tests of invalid markup for the default tree builder.

    Subclass this to test other builders.

    These are very likely to give different results for different tree
    builders. It's not required that a tree builder handle invalid
    markup at all.
    """

    @property
    def default_builder(self):
        return HTMLParserTreeBuilder()

    def test_table_containing_bare_markup(self):
        # Markup should be in table cells, not directly in the table.
        self.assertSoupEquals("<table><div>Foo</div></table>")

    def test_incorrectly_nested_table(self):
        # The second <table> tag is floating in the <tr> tag
        # rather than being inside a <td>.
        bad_markup = ('<table id="1">'
                      '<tr>'
                      "<td>Here's another table:</td>"
                      '<table id="2">'
                      '<tr><td>foo</td></tr>'
                      '</table></td>')


    def test_unclosed_a_tag(self):
        # <a> tags really ought to be closed at some point.
        #
        # We have all the <div> tags because HTML5 says to duplicate
        # the <a> tag rather than closing it, and that's what html5lib
        # does.
        markup = """<div id="1">
 <a href="foo">
</div>
<div id="2">
 <div id="3">
   <a href="bar"></a>
  </div>
</div>"""

        expect = """<div id="1">
<a href="foo">
</a></div>
<div id="2">
<div id="3">
<a href="bar"></a>
</div>
</div>"""
        self.assertSoupEquals(markup, expect)

    def test_unclosed_block_level_elements(self):
        # Unclosed block-level elements should be closed.
        self.assertSoupEquals(
            '<blockquote><p><b>Foo</blockquote><p>Bar',
            '<blockquote><p><b>Foo</b></p></blockquote><p>Bar</p>')

    def test_fake_self_closing_tag(self):
        # If a self-closing tag presents as a normal tag, it's treated
        # as one.
        self.assertSoupEquals(
            "<item><link>http://foo.com/</link></item>",
            "<item><link>http://foo.com/</link></item>")

    def test_boolean_attribute_with_no_value(self):
        soup = self.soup("<table><td nowrap>foo</td></table>")
        self.assertEqual(soup.table.td['nowrap'], None)

    def test_incorrectly_nested_tables(self):
        self.assertSoupEquals(
            '<table><tr><table><tr id="nested">',
            '<table><tr><table><tr id="nested"></tr></table></tr></table>')

    def test_floating_text_in_table(self):
        self.assertSoupEquals("<table><td></td>foo<td>bar</td></table>")

    def test_paragraphs_containing_block_display_elements(self):
        markup = self.soup("<p>this is the definition:"
                           "<dl><dt>first case</dt>")
        # The <p> tag is not closed before the <dl> tag begins.
        self.assertEqual(len(markup.p.contents), 2)

    def test_empty_element_tag_with_contents(self):
        self.assertSoupEquals("<br>foo</br>", "<br>foo</br>")

    def test_doctype_in_body(self):
        markup = "<p>one<!DOCTYPE foobar>two</p>"
        self.assertSoupEquals(markup)

    def test_nonsensical_declaration(self):
        # Declarations that don't make any sense are ignored.
        self.assertRaises(HTMLParseError, self.soup, '<! Foo = -8><p>a</p>')

    def test_whitespace_in_doctype(self):
        # A declaration that has extra whitespace is ignored.
        self.assertRaises(
            HTMLParseError, self.soup,
            '<! DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN">' +
             '<p>foo</p>')

    def test_incomplete_declaration(self):
        self.assertRaises(HTMLParseError, self.soup, 'a<!b <p>c')

    def test_cdata_where_it_doesnt_belong(self):
        #CDATA sections are ignored.
        markup = "<div><![CDATA[foo]]>"
        soup = self.soup(markup)
        self.assertEquals(soup.div.contents[0], CData("foo"))

    def test_attribute_value_never_got_closed(self):
        markup = '<a href="http://foo.com/</a> and blah and blah'
        soup = self.soup(markup)
        self.assertEqual(soup.encode(), b"")

    def test_attribute_value_with_embedded_brackets(self):
        soup = self.soup('<a b="<a>">')
        self.assertEqual(soup.a['b'], '<a>')

    def test_nonexistent_entity(self):
        soup = self.soup("<p>foo&#bar;baz</p>")
        # This is very strange.
        self.assertEqual(soup.p.string, "foo<p")

        # Compare a real entity.
        soup = self.soup("<p>foo&#100;baz</p>")
        self.assertEqual(soup.p.string, "foodbaz")

        # Also compare html5lib, which preserves the &# before the
        # entity name.

    def test_entity_out_of_range(self):
        # An entity that's out of range will be replaced with
        # REPLACEMENT CHARACTER.
        soup = self.soup("<p>&#10000000000000;</p>")
        self.assertEqual(soup.p.string, u"\N{REPLACEMENT CHARACTER}")

        soup = self.soup("<p>&#x1000000000000;</p>")
        self.assertEqual(soup.p.string, u"\N{REPLACEMENT CHARACTER}")

        soup = self.soup("<p>&#1000000000;</p>")
        self.assertEqual(soup.p.string, u"\N{REPLACEMENT CHARACTER}")


    def test_entity_was_not_finished(self):
        soup = self.soup("<p>&lt;Hello&gt")
        # Compare html5lib, which completes the entity.
        self.assertEqual(soup.p.string, "<Hello")

    def test_document_ends_with_incomplete_declaration(self):
        soup = self.soup('<p>a<!b')
        # This becomes a string 'a'. The incomplete declaration is ignored.
        # Compare html5lib, which turns it into a comment.
        self.assertEqual(soup.p.contents, ['a'])

    def test_document_starts_with_bogus_declaration(self):
        self.assertRaises(HTMLParseError, self.soup, '<! Foo ><p>a</p>')

    def test_tag_name_contains_unicode(self):
        # Unicode characters in tag names are stripped.
        tag_name = u"<our\N{SNOWMAN}>Joe</our\N{SNOWMAN}>"
        self.assertSoupEquals("<our>Joe</our>")

    def test_multiple_values_for_the_same_attribute(self):
        markup = '<b b="20" a="1" b="10" a="2" a="3" a="4"></b>'
        self.assertSoupEquals(markup, '<b a="4" b="10"></b>')

class TestHTMLParserTreeBuilderEncodingConversion(SoupTest):
    # Test Beautiful Soup's ability to decode and encode from various
    # encodings.

    @property
    def default_builder(self):
        return HTMLParserTreeBuilder()

    def setUp(self):
        super(TestHTMLParserTreeBuilderEncodingConversion, self).setUp()
        self.unicode_data = u"<html><head></head><body><foo>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</foo></body></html>"
        self.utf8_data = self.unicode_data.encode("utf-8")
        # Just so you know what it looks like.
        self.assertEqual(
            self.utf8_data,
            b"<html><head></head><body><foo>Sacr\xc3\xa9 bleu!</foo></body></html>")

    def test_ascii_in_unicode_out(self):
        # ASCII input is converted to Unicode. The original_encoding
        # attribute is set.
        ascii = b"<foo>a</foo>"
        soup_from_ascii = self.soup(ascii)
        unicode_output = soup_from_ascii.decode()
        self.assertTrue(isinstance(unicode_output, unicode))
        self.assertEqual(unicode_output, self.document_for(ascii.decode()))
        self.assertEqual(soup_from_ascii.original_encoding, "ascii")

    def test_unicode_in_unicode_out(self):
        # Unicode input is left alone. The original_encoding attribute
        # is not set.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.decode(), self.unicode_data)
        self.assertEqual(soup_from_unicode.foo.string, u'Sacr\xe9 bleu!')
        self.assertEqual(soup_from_unicode.original_encoding, None)

    def test_utf8_in_unicode_out(self):
        # UTF-8 input is converted to Unicode. The original_encoding
        # attribute is set.
        soup_from_utf8 = self.soup(self.utf8_data)
        self.assertEqual(soup_from_utf8.decode(), self.unicode_data)
        self.assertEqual(soup_from_utf8.foo.string, u'Sacr\xe9 bleu!')

    def test_utf8_out(self):
        # The internal data structures can be encoded as UTF-8.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.encode('utf-8'), self.utf8_data)

    HEBREW_DOCUMENT = b'<html><head><title>Hebrew (ISO 8859-8) in Visual Directionality</title></head><body><h1>Hebrew (ISO 8859-8) in Visual Directionality</h1>\xed\xe5\xec\xf9</body></html>'

    def test_real_hebrew_document(self):
        # A real-world test to make sure we can convert ISO-8859-9 (a
        # Hebrew encoding) to UTF-8.
        soup = self.soup(self.HEBREW_DOCUMENT,
                         from_encoding="iso-8859-8")
        self.assertEqual(soup.original_encoding, 'iso-8859-8')
        self.assertEqual(
            soup.encode('utf-8'),
            self.HEBREW_DOCUMENT.decode("iso-8859-8").encode("utf-8"))
