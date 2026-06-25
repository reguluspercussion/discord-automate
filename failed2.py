'''
[Release Note]
2026/2/11 version 1 created by M.Ishida
First Release Version
2026/6/21 version 2 created by M.Ishida
Change Notification Settings
'''

import os
import sys
import asyncio
import discord
import socket
import ast
from datetime import datetime

# =====================
# Discord 設定
# =====================
TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_NOTIFICATION"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def load_failures():
    """
    runner.py から渡された失敗情報を取得
    """
    if len(sys.argv) < 2:
        return []

    try:
        return ast.literal_eval(sys.argv[1])
    except Exception:
        return []

async def main():
    await client.login(TOKEN)

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(CHANNEL_ID)

    # 実行環境情報
    hostname = socket.gethostname()
    user = os.environ.get("USERNAME", "unknown")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    failures = load_failures()

    if failures:
        failure_text = "\n".join(
            f"- {f['script']} (rc={f['returncode']})"
            for f in failures
        )
    else:
        failure_text = "失敗情報が取得できませんでした"

    message = (
        "❌ **定期処理 エラー通知**\n"
        f"🕒 実行時刻: `{now}`\n"
        f"💻 実行端末: `{hostname}`\n"
        f"👤 実行ユーザー: `{user}`\n\n"
        "**❗ 失敗した処理:**\n"
        f"```{failure_text}```"
    )

    await channel.send(message)
    await client.close()

asyncio.run(main())
