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
    doc = Document.from_url(url)
    if debug:
        return Response(DEBUG_TEMPLATE % doc.paragraphs_detailed())
    return Response(doc.html, content_type='text/plain')

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
