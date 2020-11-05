import base64
from abc import abstractmethod

from aiohttp import web

from aiogateway.db import Token, User


@web.middleware
async def check_authorized(request: web.Request, handler):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        raise web.HTTPUnauthorized()

    auth_type, creds = auth_header.split(' ', 1)
    auth_type = auth_type.lower()
    if auth_type == 'token':
        auth_backend = TokenAuthenticationBackend
    elif auth_type == 'basic':
        auth_backend = BasicAuthenticationBackend
    else:
        raise web.HTTPBadRequest(reason='invalid auth header')

    if not await auth_backend.authenticate(creds):
        raise web.HTTPForbidden

    return await handler(request)


class BaseAuthenticationBackend:
    @classmethod
    @abstractmethod
    async def authenticate(cls, creds: str) -> bool:
        raise NotImplementedError


class TokenAuthenticationBackend(BaseAuthenticationBackend):
    @classmethod
    async def authenticate(cls, creds: str) -> bool:
        return await Token.get(creds) is not None


class BasicAuthenticationBackend(BaseAuthenticationBackend):
    @staticmethod
    def parse_basic_header(header) -> tuple:
        try:
            return tuple(base64.b64decode(header).decode().split(':', 1))
        except (ValueError, TypeError):
            raise ValueError('invalid header')

    @classmethod
    async def authenticate(cls, creds: str) -> bool:
        username, password = cls.parse_basic_header(creds)
        user = await User.get(username)
        if user is None:
            return False
        return user.check_password(password)
