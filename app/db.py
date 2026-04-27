import os
from typing import Any, Generator
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost:3306/software_license",
)


class DatabaseSession:
    def __init__(self, database_url: str):
        parsed = urlparse(database_url)
        self.connection = pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            database=parsed.path.lstrip("/"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
        )

    def fetchall(self, query: str, params: tuple[Any, ...] | list[Any] | None = None) -> list[dict[str, Any]]:
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return list(cursor.fetchall())

    def fetchone(self, query: str, params: tuple[Any, ...] | list[Any] | None = None) -> dict[str, Any] | None:
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] | None = None) -> int:
        with self.connection.cursor() as cursor:
            return cursor.execute(query, params or ())

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


def get_db() -> Generator[DatabaseSession, None, None]:
    db = DatabaseSession(DATABASE_URL)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
