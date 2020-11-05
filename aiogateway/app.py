import logging
import sqlite3

from yarl import URL
from aiohttp import web, ClientSession

import config
from aiogateway import db
from aiogateway.session import check_authorized

logger = logging.getLogger(__name__)


def parse_path(request: web.Request) -> URL:
    domain, *path = request.path.strip('/').split('/', 1)
    if not path:
        path = '/'
    else:
        path = path[0]
    url = URL(domain)
    if not url.scheme:
        url = URL(f'{request.scheme}://{domain}')
    return url.with_path(path)


async def proxy_view(request: web.Request) -> web.Response:
    url = parse_path(request)
    async with ClientSession() as session:
        logger.info(f'Make {request.method} request to {url}')
        content = await request.content.read()
        response = await session.request(
            request.method, url, params=request.query, data=content, allow_redirects=False,
        )
        logger.info(response.status)
        return web.Response(
            status=response.status, reason=response.reason, body=await response.content.read(),
            headers=response.headers,
        )


async def prepare(app: web.Application):
    app['db'] = await db.init_database()


async def shutdown(app: web.Application):
    await app['db'].close()


app = web.Application(middlewares=[check_authorized])
app.on_startup.append(prepare)
app.on_shutdown.append(shutdown)
app.router.add_route('*', '/{tail:.*}', proxy_view)
