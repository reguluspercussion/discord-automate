import os
import asyncio
import discord

# 成功通知用Botと共通
TOKEN = os.environ["DISCORD_BOT_TOKEN_WORK_NOTIFICATION"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_ERROR_NOTIFICATION"])  # エラー通知先チャンネル
LOG_FILE = "output.log"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def main():
    await client.login(TOKEN)

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(CHANNEL_ID)

    repo = os.environ.get("GITHUB_REPOSITORY", "unknown")
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}"

    # ログの最後10行を取得
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            last_lines = "".join(lines[-10:])
    else:
        last_lines = "ログが取得できませんでした"

    await channel.send(
        "❌ **GitHub Actions 失敗通知**\n"
        f"Repository: `{repo}`\n"
        f"Run URL: {run_url}\n"
        f"**Error:**\n```{last_lines}```"
    )

    await client.close()

asyncio.run(main())
