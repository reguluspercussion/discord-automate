import os
import asyncio
import discord

TOKEN = os.environ["DISCORD_BOT_TOKEN_WORK_NOTIFICATION"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_SUCCESS_NOTIFICATION"])

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

    await channel.send(
        "✅ **GitHub Actions 実行完了通知**\n"
        f"Repository: `{repo}`\n"
        f"Run URL: {run_url}"
    )

    await client.close()

asyncio.run(main())
