'''
[Release Note]
2026/2/11 version 1 created by M.Ishida
First Release Version
'''

import os
import asyncio
import discord
import socket
from datetime import datetime

# =====================
# Discord 設定
# =====================
TOKEN = os.environ["DISCORD_BOT_TOKEN_WORK_NOTIFICATION"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_SUCCESS_NOTIFICATION"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def main():
    await client.login(TOKEN)

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(CHANNEL_ID)

    # 実行環境情報
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
    await client.close()

asyncio.run(main())
