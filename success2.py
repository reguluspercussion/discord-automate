'''
[Release Note]
2026/2/11 version 1 created by M.Ishida
First Release Version
2026/2/13 version 2 created by M.Ishida
Supports Execution on GitHub
2026/6/21 version 3 created by M.Ishida
Change Notification Settings
'''

import os
import asyncio
import discord
import socket
from datetime import datetime

TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"].strip()
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_NOTIFICATION"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        channel = client.get_channel(CHANNEL_ID)
        if channel is None:
            channel = await client.fetch_channel(CHANNEL_ID)

        hostname = socket.gethostname()
        user = os.environ.get("USERNAME", "unknown")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            "✅ **定期処理 実行完了通知**\n"
            f"🕒 実行時刻: `{now}`\n"
            f"💻 実行端末: `{hostname}`\n"
            f"👤 実行ユーザー: `{user}`\n"
            "📦 ステータス: **SUCCESS**"
        )

        await channel.send(message)

    finally:
        await client.close()

async def main():
    await client.start(TOKEN)

asyncio.run(main())
