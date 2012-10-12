"""

    jaws.server -- jaws functionality exposed as WSGI application
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from urllib2 import Request as URLRequest, build_opener, HTTPCookieProcessor
from cookielib import CookieJar
from contextlib import closing
from cStringIO import StringIO

from chardet import detect
from routr import route, GET
from routrschema import qs, opt
from routr.exc import NoMatchFound
from webob import Request, Response
from webob.exc import HTTPError

from justext import justext, get_stoplist
from justext.core import output_detailed

__all__ = ('app',)

DEBUG_TEMPLATE = """
<!doctype>
<style>
.bad {
  background: #FAD9E5;
}
.good {
  background: #D9FAE0;
}
.main {
  width: 600px;
}
p {
  padding: 2px;
  margin: 0;
  margin-bottom: 5px;
}
</style>
<div class="main">%s</div>
"""

def analyse(url=None, debug=False):
    data = fetch_url(url)
    result = justext(data, get_stoplist('English'))
    if debug:
        return Response(DEBUG_TEMPLATE % output(result, output_detailed))
    return result

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

routes = route(
    GET('/analyse', qs(
            url=str,
            debug=opt(bool),
        ),
        analyse),
    )

def app(environ, start_response):
    request = Request(environ)
    try:
        tr = routes(request)
        response = tr.target(*tr.args, **tr.kwargs)
    except NoMatchFound as e:
        response = e.response
    except HTTPError as e:
        response = e
    if not isinstance(response, Response):
        response = Response(json=response)
    return response(environ, start_response)
