from aiohttp import web

import config

import logging

from aiogateway.app import app

logging.basicConfig(level=logging.DEBUG if config.DEBUG else logging.INFO)

web.run_app(app, host=config.HOST, port=config.PORT)