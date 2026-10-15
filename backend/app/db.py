import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from . import config


def conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME", "assistant"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


@contextmanager
def cursor():
    cn = conn()
    try:
        with cn.cursor() as c:
            yield c
    finally:
        cn.close()
