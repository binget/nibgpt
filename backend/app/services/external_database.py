from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from app.core.encryption import decrypt_value
from app.models.data_source import DataSource


def create_external_engine(
    source: DataSource,
) -> Engine:
    password = decrypt_value(
        source.encrypted_password
    )

    database_type = source.database_type.lower()

    if database_type == "postgresql":
        url = URL.create(
            drivername="postgresql+psycopg2",
            username=source.username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database_name,
        )

        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 15,
            },
        )

    if database_type == "mysql":
        url = URL.create(
            drivername="mysql+pymysql",
            username=source.username,
            password=password,
            host=source.host,
            port=source.port,
            database=source.database_name,
        )

        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 15,
            },
        )

    if database_type == "oracle":
        if not source.service_name:
            raise ValueError(
                "Oracle service name is required"
            )

        url = URL.create(
            drivername="oracle+oracledb",
            username=source.username,
            password=password,
            host=source.host,
            port=source.port,
            query={
                "service_name": source.service_name
            },
        )

        return create_engine(
            url,
            pool_pre_ping=True,
        )

    raise ValueError(
        f"Unsupported database type: "
        f"{source.database_type}"
    )
