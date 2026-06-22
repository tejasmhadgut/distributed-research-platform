import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5433/research_platform_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

TRUNCATE_TABLES = [
    "quant_results",
    "document_chunks",
    "sec_filings",
    "company_metrics",
    "workflow_tasks",
    "workflow_runs",
    "research_sessions",
    "users",
]


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    yield
    async with TestSessionLocal() as session:
        for table in TRUNCATE_TABLES:
            await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    from main import app
    from app.core.database import get_db

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
