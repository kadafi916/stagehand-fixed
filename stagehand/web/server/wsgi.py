import sys
import io
import os
import time
import asyncio
import inspect
import traceback
import json
import logging
import socket
from hashlib import md5

import aiohttp.web

from ...toolbox import tobytes, tostr
from . import bottle
from .bottle import Bottle, HTTPResponse, HTTPError, tob, _e, html_escape, DEBUG, RouteReset

log = logging.getLogger('stagehand.web')

class LoggingMiddleware:
    def __init__(self, application, logger):
        self._application = application
        if isinstance(logger, logging.Logger):
            self._httplog = logger
        else:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [HTTP] %(message)s'))
            self._httplog = logging.getLogger(logger)
            self._httplog.addHandler(handler)
            self._httplog.propagate = False


    def __call__(self, environ, start_response):
        bottle.response.loglevel = logging.INFO
        bottle.response.logextra = None
        t0 = time.time()

        def _start_response(status, headers, *args):
            uri = environ['PATH_INFO'] + ('?%s' % environ['QUERY_STRING'] if environ['QUERY_STRING'] else '')
            code = status.split()[0]
            size = dict(headers).get('Content-Length', '-')

            self._httplog.log(bottle.response.loglevel, '%s "%s %s %s" %s %s %.02fms%s',
                              environ['REMOTE_ADDR'], environ['REQUEST_METHOD'],
                              uri, environ['SERVER_PROTOCOL'], code, size, (time.time()-t0) * 1000.0,
                              ' ' + bottle.response.logextra if bottle.response.logextra else '')
            return start_response(status, headers, *args)

        return self._application(environ, _start_response)



class AuthMiddleware:
    def __init__(self, application, user, passwd):
        self._application = application
        self._nonce_passwd = os.urandom(64)
        self._user = user.encode()
        self._passwd = passwd.encode()


    def __call__(self, environ, start_response):
        try:
            nexthop = self._application if self._check_auth(environ) else self._auth_failed
            return nexthop(environ, start_response)
        except Exception as e:
            log.exception('error handling authentication')
            return []


    def _check_auth(self, environ):
        response = environ.get('HTTP_AUTHORIZATION')
        if not response or not response.lower().startswith('digest '):
            return False
        parts = (f.strip().split('=', 1) for f in response[7:].split(',') if '=' in f)
        rdict = dict((k.lower(), tobytes(v.strip('"'))) for k, v in parts)
        HA1 = md5(b':'.join([self._user, rdict.get('realm'), self._passwd])).hexdigest()
        HA2 = md5(b':'.join([environ.get('REQUEST_METHOD').encode(), rdict.get('uri')])).hexdigest()
        expected = md5(b':'.join([HA1.encode(), rdict.get('nonce'), HA2.encode()])).hexdigest()
        return rdict.get('response') == expected.encode()


    def _auth_failed(self, environ, start_response):
        now = tobytes(int(time.time()), coerce=True)
        nonce = now + b'/' + tobytes(md5(now + self._nonce_passwd).hexdigest())
        response_headers = [
            ('WWW-Authenticate', 'Digest realm="Secure Area", nonce="%s", algorithm=MD5' % tostr(nonce)),
            ('Content-Type', 'text/html')
        ]
        start_response('401 Authorization Required', response_headers)
        return [b"<html><body>Authorization Required</body></html>"]



class UserDataMiddleware:
    def __init__(self, application, userdict):
        self._application = application
        self._userdict = userdict


    def __call__(self, environ, start_response):
        environ.update(self._userdict)
        return self._application(environ, start_response)


class AsyncBottle(Bottle):
    async def _handle(self, environ):
        path = environ['bottle.raw_path'] = environ['PATH_INFO']
        try:
            environ['PATH_INFO'] = tostr(path)
        except UnicodeError:
            return HTTPError(400, 'Invalid path string. Expected UTF-8')

        try:
            environ['bottle.app'] = self
            try:
                self.trigger_hook("before_request")
                route, args = self.router.match(environ)
                environ['route.handle'] = route
                environ['bottle.route'] = route
                environ['route.url_args'] = args
                out = route.call(**args)
                if asyncio.iscoroutine(out) or isinstance(out, asyncio.Future):
                    out = await out
                return out
            finally:
                self.trigger_hook("after_request")
        except HTTPResponse:
            return _e()
        except RouteReset:
            route.reset()
            return (await self._handle(environ))
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            stacktrace = traceback.format_exc()
            if self.log:
                self.log.exception('error from handler')
            else:
                environ['wsgi.errors'].write(stacktrace)
            return HTTPError(500, "Internal Server Error", _e(), stacktrace)


    def _cast(self, out, peek=None):
        if isinstance(out, dict):
            bottle.response.content_type = 'application/json'
            out = json.dumps(out)
        return super()._cast(out, peek)


    async def wsgi(self, environ, start_response):
        response = bottle.response
        try:
            out = self._cast(await self._handle(environ))
            if response._status_code in (100, 101, 204, 304) \
            or environ['REQUEST_METHOD'] == 'HEAD':
                if hasattr(out, 'close'):
                    out.close()
                out = []
            start_response(response._status_line, response.headerlist)
            return out
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception:
            if not self.catchall: raise
            err = '<h1>Critical error while processing request: %s</h1>' \
                  % html_escape(environ.get('PATH_INFO', '/'))
            if bottle.DEBUG:
                err += '<h2>Error:</h2>\n<pre>\n%s\n</pre>\n' \
                       '<h2>Traceback:</h2>\n<pre>\n%s\n</pre>\n' \
                       % (html_escape(repr(_e())), html_escape(traceback.format_exc()))
            environ['wsgi.errors'].write(err)
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            start_response('500 INTERNAL SERVER ERROR', headers, sys.exc_info())
            return [tob(err)]


    async def __call__(self, environ, start_response):
        bottle.request.bind(environ)
        bottle.response.bind()
        return await self.wsgi(environ, start_response)


def _build_environ(request, body):
    environ = {
        'REQUEST_METHOD': request.method,
        'SCRIPT_NAME': '',
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query_string,
        'SERVER_NAME': request.url.host or 'localhost',
        'SERVER_PORT': str(request.url.port or 80),
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': request.scheme,
        'wsgi.input': io.BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'REMOTE_ADDR': request.remote or '127.0.0.1',
        'CONTENT_TYPE': '',
        'CONTENT_LENGTH': str(len(body)),
    }
    for key, value in request.headers.items():
        ukey = key.upper().replace('-', '_')
        if ukey == 'CONTENT_TYPE':
            environ['CONTENT_TYPE'] = value
        elif ukey == 'CONTENT_LENGTH':
            environ['CONTENT_LENGTH'] = value
        else:
            environ['HTTP_' + ukey] = value
    return environ


class Server(bottle.ServerAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = AsyncBottle()
        self._last_args = {}
        self._runner = None
        self._task = None


    def _create_server_done(self, f):
        self._task = None
        try:
            self._runner = f.result()
            log.info('started webserver at http://%s:%s/', self.host or socket.gethostname(), self.port)
        except Exception as e:
            log.error('failed to start webserver: %s', e)


    def start(self, **kwargs):
        self.loop = kwargs.pop('loop', None)
        if not self.loop:
            self.loop = asyncio.get_event_loop()
        args = self._last_args.copy()
        args.update(kwargs)
        self._last_args = args
        bottle.debug(kwargs.get('debug', False))

        app = self.app
        app.config.update(args)
        app.log = kwargs.get('log')

        if 'userdata' in kwargs:
            app = UserDataMiddleware(app, kwargs['userdata'])
        if kwargs.get('user'):
            app = AuthMiddleware(app, kwargs['user'], kwargs.get('password', ''))
        if kwargs.get('log'):
            app = LoggingMiddleware(app, kwargs['log'])

        self.host = kwargs.get('host', '')
        self.port = kwargs.get('port', 8080)
        bottle.run(app, server=self, quiet=True)
        return self._task


    def run(self, handler):
        async def wsgi_to_aiohttp(request):
            body = await request.read()
            environ = _build_environ(request, body)

            response_info = {}
            def start_response(status, headers, exc_info=None):
                response_info['status'] = status
                response_info['headers'] = list(headers)

            result = handler(environ, start_response)
            if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
                result = await result

            body_parts = []
            for part in (result or []):
                if isinstance(part, bytes):
                    body_parts.append(part)
                elif isinstance(part, str):
                    body_parts.append(part.encode('utf-8'))
            response_body = b''.join(body_parts)

            status_str = response_info.get('status', '200 OK')
            status_code = int(status_str.split()[0])
            skip_headers = {'transfer-encoding', 'content-length'}
            headers = {}
            for k, v in response_info.get('headers', []):
                if k.lower() not in skip_headers:
                    headers[k] = v

            return aiohttp.web.Response(status=status_code, headers=headers, body=response_body)

        aio_app = aiohttp.web.Application()
        aio_app.router.add_route('*', '/{path_info:.*}', wsgi_to_aiohttp)
        aio_app.router.add_route('*', '/', wsgi_to_aiohttp)

        async def start():
            runner = aiohttp.web.AppRunner(aio_app)
            await runner.setup()
            site = aiohttp.web.TCPSite(runner, self.host or None, self.port)
            await site.start()
            return runner

        self._task = asyncio.ensure_future(start())
        self._task.add_done_callback(self._create_server_done)


    def stop(self):
        if self._runner:
            log.warning('stopping web server')
            asyncio.ensure_future(self._runner.cleanup())
            self._runner = None
