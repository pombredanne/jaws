"""

    jaws -- metadata extraction toolkit
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

import re
from copy import deepcopy
from urllib2 import Request as URLRequest, build_opener, HTTPCookieProcessor
from cookielib import CookieJar
from contextlib import closing
from cStringIO import StringIO

from docopt import docopt
from chardet import detect
import lxml.html
import lxml.html.clean

import justext
import justext.core

from .utils import gen_matches_any, matches_attr, zn2
from .author import extract_author
from .image import extract_cover_image

__all__ = ('Document',)

class cached_property(object):

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        val = obj.__dict__[self.__name__] = self.func(obj)
        return val

class Document(object):
    """ Document extraction API"""

    def __init__(self, data, url=None, language='English'):
        self.data = data
        self.url = url
        self.language = language

    @classmethod
    def from_url(cls, url):
        """ Create document by fetching ``url``"""
        data = fetch_url(url)
        return cls(data, url=url)

    @classmethod
    def from_file(cls, filename):
        with open(filename) as f:
            return cls(f.read())

    @cached_property
    def parsed(self):
        """ Parsed document"""
        return lxml.html.fromstring(self.data)

    def analyse_paragraphs(self, doc):
        return justext.justext(doc, justext.get_stoplist(self.language))

    @cached_property
    def clean_doc(self):
        """ Extracted HTML content"""
        doc = deepcopy(self.parsed)
        paragraphs = self.analyse_paragraphs(doc)
        process_paragraphs(doc, paragraphs)

        remove_bad_attrs(doc)
        remove_tail(doc)

        cleaner = lxml.html.clean.Cleaner(
            scripts=True,
            javascript=True,
            style=True,
            links=True,
            meta=True,
            page_structure=True,
            forms=True,
            remove_tags=['font'],
            )
        cleaner(doc)
        garden(doc)
        return doc

    @cached_property
    def html(self):
        return lxml.html.tostring(self.clean_doc, pretty_print=True)

    @cached_property
    def text(self):
        """ Extracted text"""
        return self.clean_doc.text_content().strip()

    @cached_property
    def title(self):
        """ Try to get title of the document"""
        doc = self.parsed

        def _find_meta_title(doc):
            metas = doc.xpath('//meta[@name="title"]|//meta[@name="Title"]')
            for meta in metas:
                return meta.attrib.get('content')

        def _find_og_meta_title(doc):
            metas = doc.xpath('//meta[@property="og:title"]')
            for meta in metas:
                return meta.attrib.get('content')

        def _find_title(doc):
            titles = doc.xpath('//title')
            for title in titles:
                text = title.text_content().strip()
                if text:
                    return text

        def _headers(doc):
            # not sure if need to look for h4, h5, h6, ...
            return doc.xpath('//h1|//h2|//h3|//h4|//h5|//h6')

        def _clean(title, doc):
            found = [] # (text, header level)
            for h in  _headers(doc):
                text = h.text_content().strip()
                if text and zn2(text) in zn2(title) and not title in text:
                    found.append((text, int(h.tag[1:])))
            if found:
                found.sort(key=lambda (t, l): (-len(t), -l))
                return found[0][0]
            return title.strip()

        for finder in (_find_meta_title, _find_og_meta_title, _find_title):
            title = finder(doc)
            if title:
                return _clean(title, doc)

    @cached_property
    def author(self):
        return extract_author(deepcopy(self.parsed))

    @cached_property
    def cover_image(self):
        assert self.url is not None
        doc = deepcopy(self.parsed)
        paragraphs = self.analyse_paragraphs(doc)
        return extract_cover_image(doc, self.url, paragraphs=paragraphs)

def bottom_up_traverse(root):
    for e in root:
        if len(e) > 0:
            for x in bottom_up_traverse(e):
                yield x
        yield e

def is_good(e):
    return (
        e.attrib.get('good')
        or e.xpath('*[@good="true"]'))

def remove_tail(root):
    e = root.xpath('//*[@good="true"]')
    if not e:
        return
    e = e[-1]

    while e.getparent() is not None:
        cur = e
        while cur.getnext() is not None:
            next = e.getnext()
            if not is_good(next):
                next.drop_tree()
            cur = next
        e = e.getparent()

def garden(root):
    # normalize text content
    for el in list(root.iter()):
        for attr in ('class', 'id'):
            if attr in el.attrib:
                el.attrib.pop(attr)
        if el.text and re.search('[a-zA-Z]', el.text):
            el.text = re.sub('[\t\n\r]+', ' ', el.text)
            el.text = re.sub('[ ]+', ' ', el.text)
        else:
            el.text = None

        if el.tail and re.search('[a-zA-Z]', el.tail):
            el.tail = re.sub('[\t\n\r]+', ' ', el.tail)
            el.tail = re.sub('[ ]+', ' ', el.tail)
        else:
            el.tail = None

    for el in list(bottom_up_traverse(root)):
        # remove all elems which have no content
        if (len(el) == 0
                and el.tag not in ('img',)
                and not el.text
                and el.getparent() is not None):
            el.drop_tree()

        # unwrap elements which only do
        if (len(el) == 1
                and not el.text
                and el.getparent() is not None):
            el.drop_tag()

def process_paragraphs(root, paragraphs):
    """ Remove nodes which were classified as "bad" by justext algo"""
    to_delete = []
    for p in paragraphs:
        if p['class'] == 'bad':
            to_delete.extend(root.xpath(p['xpath']))
        elif p['class'] == 'good':
            for e in root.xpath(p['xpath']):
                e.attrib['good'] = 'true'
    for el in reversed(to_delete):
        if el.getparent() is not None:
            el.drop_tree()

def remove_bad_attrs(root):
    """ Remove nodes which have "bad" class or id attributes"""
    for el in list(bottom_up_traverse(root)):
        if matches_attr(_very_bad_attr_re, el, 'class', 'id'):
            el.drop_tree()
        elif (
            matches_attr(_bad_attr_re, el, 'class', 'id')
            and not any(
                matches_attr(_good_attr_re, x, 'class', 'id')
                for x in el.iter())):

            el.drop_tree()

def output(result, formatter):
    fp = StringIO()
    formatter(result, fp=fp)
    fp.seek(0, 0)
    return fp.read()

def fetch_url(url):
    """ Fetch URL using sane UA and encoding processing"""
    request = URLRequest(url, None, {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8)'
            'AppleWebKit/536.25 (KHTML, like Gecko)'
            'Version/6.0 Safari/536.25')
        })
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with closing(opener.open(request)):
        data = opener.open(request).read()
    enc = detect(data).get('encoding')
    if enc:
        data = data.decode(enc).encode('utf8')
    return data

_very_bad_attr_re = gen_matches_any(
    'comment',
    'discuss',
    )
_bad_attr_re = gen_matches_any(
    'sidebar',
    'tweet',
    'header',
    'contact',
    'login',
    'foot',
    'popup',
    'promo',
    'combx',
    'com-',
    'masthead',
    '^media$',
    'meta',
    'outbrain',
    'related',
    'scroll',
    'shoutbox',
    'sponsor',
    'shopping',
    'tags',
    'tool',
    'widget',
    'print',
    'taxonom',
    'e[\-]?mail',
    'share',
    'reply',
    'sign',
    'caption',
    'ad-',
    'subscri',
    'buy',
    '(^|\-|_)date($|\-|_)',
    )

_good_attr_re = gen_matches_any(
    'article',
    'body',
    'content',
    'entry',
    'hentry',
    'main',
    'page',
    'pagination',
    'post',
    'text',
    'blog',
    'story',
    )

def main():
    args = docopt("""
usage: jaws [-h] (--html | --text | --title | --image) URL

options:
    -h, --help              show this message and exit

    --html              html
    -t, --text              text
    --title                 title
    -a, --author            author
    -i, --image             image
""")

    url = args['URL']
    if url.lower().startswith('http'):
        doc = Document.from_url(url)
    else:
        doc = Document.from_file(url)
    if args['--text']:
        print doc.text
    elif args['--title']:
        print doc.title
    elif args['--author']:
        print doc.author
    elif args['--image']:
        print doc.cover_image
    else:
        print doc.html
