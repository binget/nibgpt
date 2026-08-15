from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from app.core.encryption import decrypt_value
from app.models.data_source import DataSource


def test_postgresql(source: DataSource) -> None:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=source.username,
        password=decrypt_value(source.encrypted_password),
        host=source.host,
        port=source.port,
        database=source.database_name,
    )

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def test_mysql(source: DataSource) -> None:
    url = URL.create(
        drivername="mysql+pymysql",
        username=source.username,
        password=decrypt_value(source.encrypted_password),
        host=source.host,
        port=source.port,
        database=source.database_name,
    )

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def test_oracle(source: DataSource) -> None:
    import oracledb

    password = decrypt_value(source.encrypted_password)

    if not source.service_name:
        raise ValueError(
            "Oracle service name is required"
        )

    connection: Any = oracledb.connect(
        user=source.username,
        password=password,
        host=source.host,
        port=source.port,
        service_name=source.service_name,
    )

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM DUAL")
        cursor.fetchone()
        cursor.close()
    finally:
        connection.close()


def test_data_source(source: DataSource) -> None:
    database_type = source.database_type.lower()

    if database_type == "postgresql":
        test_postgresql(source)
        return

    if database_type == "mysql":
        test_mysql(source)
        return

    if database_type == "oracle":
        test_oracle(source)
        return

    raise ValueError(
        f"Unsupported database type: {source.database_type}"
    )
