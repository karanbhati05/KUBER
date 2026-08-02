from sqlalchemy.ext.asyncio import create_async_engine , AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+aiomysql://root:password@localhost:3307/kuber_db"

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine,
    class_ = AsyncSession
)

async def get_db():
    async with SessionLocal() as session:
        yield session 
    
