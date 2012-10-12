"""

    jaws -- metadata extraction toolkit
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from urllib2 import Request as URLRequest, build_opener, HTTPCookieProcessor
from cookielib import CookieJar
from contextlib import closing
from cStringIO import StringIO
from chardet import detect
import lxml.html
import justext
import justext.core

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

    def __init__(self, data, language='English'):
        self.data = data
        self.language = language

    @cached_property
    def parsed(self):
        return lxml.html.fromstring(self.data)

    @cached_property
    def paragraphs(self):
        return justext.justext(self.parsed, justext.get_stoplist(self.language))

    def paragraphs_detailed(self):
        return output(self.paragraphs, justext.core.output_detailed)

    @cached_property
    def text(self):
        return ' '.join(p['text'] for p in self.paragraphs)

    @classmethod
    def from_url(cls, url):
        data = fetch_url(url)
        return cls(data)

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
