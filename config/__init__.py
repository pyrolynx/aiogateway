import ast
import os

from .base import *

_env_upd = {}
for env in list(locals()):
    value = os.getenv(env)
    if value is not None:
        try:
            value = ast.literal_eval(value)
        except SyntaxError:
            value = value
        _env_upd[env] = value
locals().update(_env_upd)
del _env_upd
