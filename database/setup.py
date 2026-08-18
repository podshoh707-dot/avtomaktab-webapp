import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models import Base

# SQLite bilan ishlash (lokal). Keyin PostgreSQL ga o'tkazish ham mumkin.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "database.sqlite")
DB_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    def _sync_schema(sync_conn):
        from sqlalchemy import inspect, text
        Base.metadata.create_all(sync_conn)
        inspector = inspect(sync_conn)
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_cols = {col['name'] for col in inspector.get_columns(table_name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        col_type = col.type.compile(sync_conn.dialect)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
                        try:
                            sync_conn.execute(text(sql))
                            print(f"Auto-migrated column: {table_name}.{col.name}")
                        except Exception as e:
                            print(f"Migration error ({table_name}.{col.name}): {e}")

    async with engine.begin() as conn:
        await conn.run_sync(_sync_schema)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
