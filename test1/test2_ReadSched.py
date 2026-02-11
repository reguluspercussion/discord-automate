import discord
import os
from datetime import datetime, timedelta, timezone
import re

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_TEST_SCHED"])

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def fetch_recent_messages():
    await client.wait_until_ready()
    thread = await client.fetch_channel(CHANNEL_ID)

    now_utc = datetime.now(timezone.utc)
    yesterday_utc = now_utc - timedelta(days=1)

    messages = []
    async for message in thread.history(limit=100, after=yesterday_utc):
        if not message.author.bot and message.content:
            messages.append({
                "content": message.content,
                "timestamp": message.created_at
            })

    return messages

def extract_schedule_data(text: str):
    """
    改行を含む文字列を加工し、日付・開始時刻・終了時刻・場所を抽出
    """
    if not text:
        return []

    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "/" in line:
            try:
                date_match = re.search(r'\b(\d{1,2}/\d{1,2})\b', line)
                if not date_match:
                    i += 1
                    continue

                date_str = date_match.group(1)
                times = re.findall(r'\b\d{1,2}:\d{2}\b', line)
                if len(times) < 1:
                    i += 1
                    continue

                start_time = times[0]
                end_time = times[1] if len(times) > 1 else None

                place1 = lines[i+1].strip() if i+1 < len(lines) else None
                place2 = lines[i+2].strip() if i+2 < len(lines) else None
                place = " ".join(filter(None, [place1, place2]))

                result.append({
                    "date": date_str,
                    "start_time": start_time,
                    "end_time": end_time,
                    "place": place
                })

                i += 3
                continue

            except Exception as e:
                print(f"行スキップ: {line} ({e})")
                i += 1
                continue

        i += 1

    return result

@client.event
async def on_ready():
    messages = await fetch_recent_messages()

    # 「月の練習予定」を含む最新メッセージのみ抽出
    target_messages = [m for m in messages if "月の練習予定" in m["content"]]
    if target_messages:
        latest_message = max(target_messages, key=lambda x: x["timestamp"])
        schedule_data = extract_schedule_data(latest_message["content"])
        print(schedule_data)
    else:
        print("直近24時間以内に対象のメッセージはありません")

    await client.close()

client.run(TOKEN)
