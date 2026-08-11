import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Aiven MySQL admin connection string from environment
AIVEN_ADMIN_URL = os.getenv("AIVEN_ADMIN_URL", "mysql+aiomysql://root:password@localhost:3306/defaultdb")

async def init_aiven_databases():
    print("==========================================================================")
    print("          INITIALIZING AIVEN CLOUD MYSQL SHARD DATABASES                 ")
    print("==========================================================================")

    # Connect to Aiven defaultdb with isolation level AUTOCOMMIT for CREATE DATABASE
    engine = create_async_engine(AIVEN_ADMIN_URL, isolation_level="AUTOCOMMIT", echo=True)

    databases_to_create = ["kuber_db_mumbai", "kuber_db_delhi"]

    async with engine.connect() as conn:
        for db_name in databases_to_create:
            try:
                await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name};"))
                print(f" [SUCCESS] Database '{db_name}' created or verified on Aiven Cloud!")
            except Exception as e:
                print(f" [ERROR] Failed to create database '{db_name}': {e}")

    await engine.dispose()
    print("--------------------------------------------------------------------------")
    print(" Aiven MySQL Shard Databases Ready for KUBER Billing Engine!")
    print("==========================================================================\n")

if __name__ == "__main__":
    asyncio.run(init_aiven_databases())
