= Introduction =

  >>> from bs4 import BeautifulSoup
  >>> soup = BeautifulSoup("<p>Some<b>bad<i>HTML")
  >>> print soup.prettify()
  <html>
   <body>
    <p>
     Some
     <b>
      bad
      <i>
       HTML
      </i>
     </b>
    </p>
   </body>
  </html>
  >>> soup.find(text="bad")
  u'bad'

  >>> soup.i
  <i>HTML</i>

  >>> soup = BeautifulSoup("<tag1>Some<tag2/>bad<tag3>XML", "xml")
  >>> print soup.prettify()
  <?xml version="1.0" encoding="utf-8">
  <tag1>
   Some
   <tag2 />
   bad
   <tag3>
    XML
   </tag3>
  </tag1>

The bs4/doc directory contains full documentation in Sphinx
format. Run "make html" to create HTML documentation.

= Running the unit tests =

Here's how to run the tests on Python 2.7:

 $ cd bs4
 $ python2.7 -m unittest discover -s bs4

Here's how to do it with Python 3.2:

 $ ./convert-py3k
 $ cd py3k/bs4
 $ python3 -m unittest discover -s bs4

The script test-all-versions will run the tests twice, once on Python
2.7 and once on Python 3.
