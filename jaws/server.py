"""

    jaws.server -- jaws functionality exposed as WSGI application
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""

from routr import route, GET
from routrschema import qs, opt
from routr.exc import NoMatchFound
from webob import Request, Response
from webob.exc import HTTPError
from . import Document

__all__ = ('app',)

def analyse(url=None, html=False, text=False, image=False, author=False,
        title=False):
    doc = Document.from_url(url)
    result = {}
    if html:
        result['html'] = doc.html
    if text:
        result['text'] = doc.text
    if image:
        result['image'] = doc.image
    if author:
        result['author'] = doc.author
    if title:
        result['title'] = doc.title
    return result

routes = route(
    GET('/analyse', qs(
            url=str,
            image=opt(bool),
            text=opt(bool),
            html=opt(bool),
            title=opt(bool),
            author=opt(bool),
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
