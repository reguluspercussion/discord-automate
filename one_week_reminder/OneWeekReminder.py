'''
[Release Note]
2026/2/13 version 1 created by M.Ishida
First Release Version
'''

import os
import ssl
from datetime import date, timedelta

import asyncpg
import discord

# ========= Discord =========
intents = discord.Intents.default()
client = discord.Client(intents=intents)

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
MUSIC_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_MUSIC_COMMITEE"])
THREAD_ID = int(os.environ["DISCORD_CHANNEL_ID_TEST_POST"])


# ========= DB =========
async def get_db_conn():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        database=os.environ["DB_DATABASE"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        ssl=ssl_ctx,
        timeout=10,
    )


@client.event
async def on_ready():
    await process_schedule()
    await client.close()


async def process_schedule():
    today = date.today()
    limit_date = today + timedelta(days=7)

    conn = await get_db_conn()

    try:
        rows = await conn.fetch(
            """
            SELECT
                id,
                practice_date,
                start_time,
                end_time,
                place
            FROM schedule
            WHERE announce = FALSE
              AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date
        )

        if not rows:
            print("通知対象なし")
            return

        thread = await client.fetch_channel(THREAD_ID)

        for r in rows:
            # 秒を除外した時刻フォーマット
            start_str = r["start_time"].strftime("%H:%M")
            end_str = r["end_time"].strftime("%H:%M")

            message = (
                f"<@&{MUSIC_ROLE_ID}>\n"
                f"📢 **練習予定の確定をお願いします**\n\n"
                f"🗓 日付：**{r['practice_date']}**\n"
                f"⏰ 時間：**{start_str}〜{end_str}**\n"
                f"📍 場所：**{r['place']}**\n\n"
                f"※ 練習日まで7日を切っています。"
            )

            await thread.send(message)

            await conn.execute(
                """
                UPDATE schedule
                SET announce = TRUE
                WHERE id = $1
                """,
                r["id"]
            )

            print(f"通知・更新完了 id={r['id']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
