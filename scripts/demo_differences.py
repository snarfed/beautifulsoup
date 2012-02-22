from bs4 import BeautifulSoup

different_results = []
uniform_results = []

class Demonstration(object):
    def __init__(self, markup):
        self.results = {}
        self.markup = markup

    def run_against(self, *parser_names):
        uniform_results = True
        previous_output = None
        for parser in parser_names:
            try:
                soup = BeautifulSoup(self.markup, parser)
                if markup.startswith("<div>"):
                    # Extract the interesting part
                    output = soup.div
                else:
                    output = soup
            except Exception, e:
                output = "[EXCEPTION] %s" % str(e)
            self.results[parser] = output
            if previous_output is None:
                previous_output = output
            elif previous_output != output:
                uniform_results = False
        return uniform_results

    def dump(self):
        print "%s: %s" % ("Markup".rjust(13), self.markup.encode("utf8"))
        for parser, output in self.results.items():
            print "%s: %s" % (parser.rjust(13), output.encode("utf8"))


for markup in open("differences.txt"):
    demo = Demonstration(markup.decode("utf8").strip().replace("\\n", "\n"))
    is_uniform = demo.run_against("html.parser", "lxml", "html5lib")
    if is_uniform:
        uniform_results.append(demo)
    else:
        different_results.append(demo)

print "Markup that's handled the same in every parser:"
for demo in uniform_results:
    demo.dump()
    print "-" * 80
print
print "=" * 80
print
print "Markup that's not handled the same in every parser:"
for demo in different_results:
    demo.dump()
    print "-" * 80
