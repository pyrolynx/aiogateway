import dataclasses
import hashlib
from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import Optional, List

import aiosqlite

import config


async def init_database() -> aiosqlite.Connection:
    def dict_cursor_factory(cursor: aiosqlite.Cursor, row: tuple):
        result = {}
        for idx, column in enumerate(cursor.description):
            result[column[0]] = row[idx]
        return result

    database = await aiosqlite.connect(config.DB_NAME)
    database.row_factory = dict_cursor_factory
    models = []
    for obj in globals().values():
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            models.append(obj)
    for model in models:
        model._database = database
        await model.create_table()
    return database


class ModelMeta(type):
    _database: aiosqlite.Connection
    __schema__: List[tuple]
    __table__: str

    @property
    def database(self):
        assert hasattr(self, '_database')
        return self._database

    @asynccontextmanager
    async def db_cursor(self) -> aiosqlite.Cursor:
        cursor = await self.database.cursor()
        yield cursor
        await cursor.close()

    async def create_table(self):
        assert hasattr(self, '_database'), 'Database is not inited'
        async with self.db_cursor() as cursor:
            columns = ',\n'.join([' '.join(column) for column in self.__schema__])
            await cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.__table__} ({columns})")


class BaseModel(metaclass=ModelMeta):
    @property
    @abstractmethod
    def __table__(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def __schema__(self):
        raise NotImplementedError

    @classmethod
    @abstractmethod
    async def get(cls, *args, **kwargs):
        raise NotImplementedError


@dataclasses.dataclass
class User(BaseModel):
    __table__ = 'users'
    __schema__ = [("username", "TEXT", "NOT NULL", "UNIQUE"), ("password", "TEXT", "NOT NULL")]
    username: str
    password: str = dataclasses.field(repr=False)

    @classmethod
    async def get(cls, username: str) -> Optional["User"]:
        async with cls.db_cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute(f"SELECT username, password FROM users WHERE username=?", (username,))
            user_data = await cursor.fetchone()
            if user_data is None:
                return None
            return cls(**user_data)

    def check_password(self, raw_password: str):
        return self.password == hashlib.sha256(raw_password.encode()).hexdigest()


class Token(str, BaseModel):
    __table__ = 'tokens'
    __schema__ = [("token", "TEXT", "PRIMARY KEY")]

    @classmethod
    async def get(cls, token: str) -> Optional["Token"]:
        async with cls.db_cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute(f"SELECT token FROM tokens WHERE token=?", (token,))
            token_data = await cursor.fetchone()
            if token_data is None:
                return None
            return cls(token_data["token"])
