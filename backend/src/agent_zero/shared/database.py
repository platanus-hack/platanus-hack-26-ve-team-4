from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Fixed key of the advisory lock that replaces BEGIN IMMEDIATE on Postgres. Advisory locks are
# local to each database, so the protected store and the honeypot do not block each other,
# just like their separate SQLite files.
WRITE_LOCK_KEY = 0x6167_7A65_726F


class AppBase(DeclarativeBase):
    pass


def is_postgres(url: str) -> bool:
    return make_url(url).get_backend_name() == "postgresql"


class Database:
    def __init__(self, url: str, pool_size: int = 5, max_overflow: int = 10) -> None:
        if is_postgres(url):
            self.engine: AsyncEngine = create_async_engine(
                url, pool_pre_ping=True, pool_size=pool_size, max_overflow=max_overflow
            )
        else:
            self.engine = create_async_engine(url)
        self.sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(AppBase.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()


async def acquire_write_lock(db: AsyncSession) -> None:
    """Serialize every writer that calls this, like SQLite's BEGIN IMMEDIATE.

    SQLite takes the database writer reservation. Postgres takes a transaction-scoped advisory
    lock, released on commit or rollback. Call it before the first read of the transaction.
    """
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": WRITE_LOCK_KEY})
    else:
        await db.execute(text("BEGIN IMMEDIATE"))


async def begin_snapshot(db: AsyncSession) -> None:
    """Read several tables from one consistent snapshot."""
    if db.get_bind().dialect.name == "postgresql":
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
    else:
        await db.execute(text("BEGIN"))


async def ensure_database(url: str) -> None:
    """Create the Postgres database named in the URL when it does not exist yet."""
    if not is_postgres(url):
        return
    target = make_url(url)
    if not target.database:
        raise ValueError("La URL de Postgres debe nombrar una base.")
    admin = create_async_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            )
            if not exists:
                name = connection.dialect.identifier_preparer.quote(target.database)
                await connection.execute(text(f"CREATE DATABASE {name}"))
    finally:
        await admin.dispose()
