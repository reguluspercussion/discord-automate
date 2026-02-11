import discord
import os
import asyncio
import asyncpg
import ssl
import re
from datetime import datetime, timedelta, timezone, date

# =====================
# Discord 設定
# =====================
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_TEST_SCHED"])

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# =====================
# Supabase(DB) 接続
# =====================
async def get_db_connection():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=5432,
        database="postgres",
        user="postgres",
        password=os.environ["DB_PASSWORD"],
        ssl=ssl_ctx,
        timeout=10,
    )

# =====================
# Discord メッセージ取得
# =====================
async def fetch_recent_messages():
    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)

    messages = []
    async for message in channel.history(limit=100, after=yesterday_utc):
        if not message.author.bot and message.content:
            messages.append({
                "content": message.content,
                "timestamp": message.created_at
            })

    return messages

# =====================
# スケジュール抽出
# =====================
def extract_schedule_data(text: str):
    if not text:
        return []

    lines = text.splitlines()
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if "/" in line:
            date_match = re.search(r'\b(\d{1,2}/\d{1,2})\b', line)
            times = re.findall(r'\b\d{1,2}:\d{2}\b', line)

            if date_match and len(times) >= 2:
                place1 = lines[i + 1].strip() if i + 1 < len(lines) else ""
                place2 = lines[i + 2].strip() if i + 2 < len(lines) else ""

                result.append({
                    "date": date_match.group(1),
                    "start_time": times[0],
                    "end_time": times[1],
                    "place": f"{place1} {place2}".strip()
                })

                i += 3
                continue

        i += 1

    return result

# =====================
# DB INSERT
# =====================
async def insert_schedules(conn, schedules):
    sql = """
        INSERT INTO test_schedule
        (practice_date, start_time, end_time, place)
        VALUES ($1, $2, $3, $4)
    """

    current_year = datetime.now().year

    for s in schedules:
        month, day = map(int, s["date"].split("/"))
        practice_date = date(current_year, month, day)

        # ★ 重要：str → datetime.time
        start_time = datetime.strptime(s["start_time"], "%H:%M").time()
        end_time   = datetime.strptime(s["end_time"], "%H:%M").time()

        await conn.execute(
            sql,
            practice_date,
            start_time,
            end_time,
            s["place"]
        )

# =====================
# Discord 起動イベント
# =====================
@client.event
async def on_ready():
    messages = await fetch_recent_messages()

    target_messages = [
        m for m in messages
        if "月の練習予定" in m["content"]
    ]

    if not target_messages:
        print("対象メッセージなし")
        await client.close()
        return

    latest_message = max(
        target_messages,
        key=lambda x: x["timestamp"]
    )

    schedules = extract_schedule_data(latest_message["content"])

    if not schedules:
        print("抽出データなし")
        await client.close()
        return

    conn = await get_db_connection()
    await insert_schedules(conn, schedules)
    await conn.close()

    print(f"{len(schedules)} 件 INSERT 完了")
    await client.close()

# =====================
# 実行
# =====================
client.run(TOKEN)
