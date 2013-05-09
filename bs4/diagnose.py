"""Diagnostic functions, mainly for use when doing tech support."""
from StringIO import StringIO
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup, __version__
from bs4.builder import builder_registry
import os
import random
import traceback
import sys

def diagnose(data):
    """Diagnostic suite for isolating common problems."""
    print "Diagnostic running on Beautiful Soup %s" % __version__
    print "Python version %s" % sys.version

    if hasattr(data, 'read'):
        data = data.read()
    elif os.path.exists(data):
        print '"%s" looks like a filename. Reading data from the file.' % data
        data = open(data).read()
    basic_parsers = ["html.parser", "html5lib", "lxml"]
    for name in basic_parsers:
        for builder in builder_registry.builders:
            if name in builder.features:
                break
        else:
            basic_parsers.remove(name)
            print (
                "I noticed that %s is not installed. Installing it may help." %
                name)

    if 'lxml' in basic_parsers:
        basic_parsers.append(["lxml", "xml"])
        from lxml import etree
        print "Found lxml version %s" % ".".join(map(str,etree.LXML_VERSION))

    if 'html5lib' in basic_parsers:
        import html5lib
        print "Found html5lib version %s" % html5lib.__version__
    print

    for parser in basic_parsers:
        print "Trying to parse your markup with %s" % parser
        success = False
        try:
            soup = BeautifulSoup(data, parser)
            success = True
        except Exception, e:
            print "%s could not parse the markup." % parser
            traceback.print_exc()
        if success:
            print "Here's what %s did with the markup:" % parser
            print soup.prettify()

        print "-" * 80

def lxml_trace(data, html=True):
    """Print out the lxml events that occur during parsing.

    This lets you see how lxml parses a document when no Beautiful
    Soup code is running.
    """
    from lxml import etree
    for event, element in etree.iterparse(StringIO(data), html=html):
        print("%s, %4s, %s" % (event, element.tag, element.text))

class AnnouncingParser(HTMLParser):
    """Announces HTMLParser parse events, without doing anything else."""
    def handle_starttag(self, name, attrs):
        print "%s START" % name

    def handle_endtag(self, name):
        print "%s END" % name

    def handle_data(self, data):
        print "%s DATA" % data

    def handle_charref(self, name):
        print "%s CHARREF" % name

    def handle_entityref(self, name):
        print "%s ENTITYREF" % name

    def handle_comment(self, data):
        print "%s COMMENT" % data

    def handle_decl(self, data):
        print "%s DECL" % data

    def unknown_decl(self, data):
        print "%s UNKNOWN-DECL" % data

    def handle_pi(self, data):
        print "%s PI" % data

def htmlparser_trace(data):
    """Print out the HTMLParser events that occur during parsing.

    This lets you see how HTMLParser parses a document when no
    Beautiful Soup code is running.
    """
    parser = AnnouncingParser()
    parser.feed(data)

_vowels = "aeiou"
_consonants = "bcdfghjklmnpqrstvwxyz"

def rword(length=5):
    "Generate a random word-like string."
    s = ''
    for i in range(length):
        if i % 2 == 0:
            t = _consonants
        else:
            t = _vowels
        s += random.choice(t)
    return s

def rsentence(length=4):
    "Generate a random sentence-like string."
    return " ".join(rword(random.randint(4,9)) for i in range(length))
        
def rdoc(num_elements=1000):
    """Randomly generate an invalid HTML document."""
    tag_names = ['p', 'div', 'span', 'i', 'b', 'script', 'table']
    elements = []
    for i in range(num_elements):
        choice = random.randint(0,3)
        if choice == 0:
            # New tag.
            tag_name = random.choice(tag_names)
            elements.append("<%s>" % tag_name)
        elif choice == 1:
            elements.append(rsentence(random.randint(1,4)))
        elif choice == 2:
            # Close a tag.
            tag_name = random.choice(tag_names)
            elements.append("</%s>" % tag_name)
    return "\n".join(elements)


if __name__ == '__main__':
    diagnose(sys.stdin.read())
