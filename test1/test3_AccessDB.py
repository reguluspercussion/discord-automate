import asyncio
import asyncpg
import ssl
import os

async def main():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=5432,
        database="postgres",
        user="postgres",
        password=os.environ["DB_PASSWORD"],
        ssl=ssl_ctx,
        timeout=10,
    )

    row = await conn.fetchrow("SELECT 1;")
    print("OK:", row[0])

    await conn.close()

asyncio.run(main())
