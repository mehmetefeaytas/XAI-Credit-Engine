"""
app/data/database.py
──────────────────────────────────────────────────────────────────────────────
Veritabanı bağlantısı ve Asenkron oturum (session) yönetimi.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import get_settings

settings = get_settings()

# Asenkron Engine oluştur
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    # SQLite kullanırken tablo eşzamanlılığı parametrelerine ihtiyaç duymayabiliriz
    # ancak PostgreSQL'e geçtiğimizde pool_size gibi parametreler burada aktif edilebilir.
)

# Her işlem için asenkron oturum sağlayıcı
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Tüm tabloların türeyeceği miras (base) sınıfı
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Depends() enjeksiyonu için asenkron DB oturum üreteci.
    
    Kullanım:
        @app.get("/endpoint")
        async def endpoint_handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
