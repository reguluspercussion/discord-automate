'''
[Release Note]
2026/X/XX version 1 created by M.Ishida
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
#MUSIC_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_MUSIC_COMMITEE"])
#THREAD_ID = int(os.environ["DISCORD_CHANNEL_ID_MUSIC_COMMITEE"])

#CARRIER_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_CARRIER"])
#CARRIER_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_CARRIER"])
#PERCUSSION_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_PERCUSSION"])

CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_MONTHLY_SCHEDULE"])

ATTENDING = "<:syusseki:1244649880576720977>"
ABSENT = "<:kesseki:1244642454745907384>"
LATE = "<:chikoku:1244649936612626472>"
LEAVINGEARLY = "<:soutai:1244642518197600336>"
TBD = "<:mitei:1244642545221369971>"

# ========= DB =========
async def get_db_conn():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
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
    limit_date_1m = today + timedelta(days=30)
    limit_date_2w = today + timedelta(days=14)
    limit_date_1w = today + timedelta(days=7)
    limit_date_1d = today + timedelta(days=1)

    conn = await get_db_conn()

    # ==============================
    # 1ヶ月前のスレッド作成
    # ==============================
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
            WHERE announce_1m = FALSE
              AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_1m
        )

        if not rows:
            print("通知対象なし")
            return
        
        # ==============================
        # 出欠依頼
        # ==============================
        #thread = await client.fetch_channel(THREAD_ID)

        for r in rows:
            # 秒を除外した時刻フォーマット
            start_str = r["start_time"].strftime("%H:%M")
            end_str = r["end_time"].strftime("%H:%M")

            channel = await client.fetch_channel(CHANNEL_ID)

            thread_name = f"{r['practice_date'].month}/{r['practice_date'].day}@{r['place']}"

            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread
            )

            thread_id = thread.id

            message = (
                f"@everyone\n"
                f"📢 **出欠の入力をお願いします**\n\n"
                f"🗓 日付：**{r['practice_date']}**\n"
                f"⏰ 時間：**{start_str}〜{end_str}**\n"
                f"📍 場所：**{r['place']}**\n\n"
                f"※ 練習日まで1ヶ月となりました。\n"
                f"{r['ATTENDING''ABSENT''LATE''LEAVINGEARLY''TBD']}のどれかを入力してください"
            )

            await thread.send(message)
            '''
            # ==============================
            # 運び屋さん募集スレッド作成
            # ==============================
            carrier_channel = await client.fetch_channel(CARRIER_CHANNEL_ID)

            thread_name = f"{r['practice_date'].month}/{r['practice_date'].day}@{r['place']}"

            carrier_thread = await carrier_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread
            )

            carrier_message = (
                f"<@&{CARRIER_ROLE_ID}> <@&{PERCUSSION_ROLE_ID}>\n"
                f"🚚 **楽器運搬ご協力のお願い**\n\n"
                f"🗓 日付：**{r['practice_date']}**\n"
                f"📍 場所：**{r['place']}**\n\n"
                f"楽器運搬をお手伝いいただける方は、このスレッドに返信をお願いします！"
            )

            await carrier_thread.send(carrier_message)
            '''
            await conn.execute(
                """
                UPDATE schedule
                SET announce_1m = TRUE,
                    thread_id = $2
                WHERE id = $1
                """,
                r["id"],
                thread_id
            )

            print(f"通知・更新完了 id={r['id']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
