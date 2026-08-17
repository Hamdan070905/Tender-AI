from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Convert sync database URL to async driver URL & resolve absolute SQLite path
db_url = settings.POSTGRES_URL

if "sqlite" in db_url:
    if ":///" in db_url:
        driver_prefix, raw_path = db_url.split(":///", 1)
        # Handle driver conversion if needed
        if "aiosqlite" not in driver_prefix:
            driver_prefix = "sqlite+aiosqlite"
        
        path_obj = Path(raw_path)
        if not path_obj.is_absolute():
            clean_path = raw_path.lstrip("./").lstrip("/")
            abs_db_path = (BASE_DIR / clean_path).resolve()
            async_url = f"{driver_prefix}:///{abs_db_path.as_posix()}"
        else:
            async_url = f"{driver_prefix}:///{path_obj.as_posix()}"
    else:
        async_url = db_url
elif db_url.startswith("postgresql://"):
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    async_url = db_url

engine = create_async_engine(
    async_url,
    pool_pre_ping=True,
    echo=settings.APP_ENV == "development",
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup (dev only; use alembic in prod)."""
    async with engine.begin() as conn:
        from models import user, tender, proposal  # noqa: import triggers registration
        await conn.run_sync(Base.metadata.create_all)

    # Ensure dev user exists in database
    async with AsyncSessionLocal() as session:
        from models.user import User
        dev_user = await session.get(User, "dev_user_001")
        if not dev_user:
            dev_user = User(
                id="dev_user_001",
                email="dev@tenderai.local",
                hashed_password="dev_password_hash",
                full_name="Dev Architect",
                company_name="3D Concrete Tech",
                company_description="We manufacture concrete 3D printers for construction automation and additive manufacturing in infrastructure projects.",
                company_profile={"certs": ["ISO9001"], "experience": "5+ years"},
                plan="pro",
                is_active=True,
            )
            session.add(dev_user)
            await session.commit()
