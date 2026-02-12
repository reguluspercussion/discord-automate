import os
import discord

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_TEST_POST"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    channel = client.get_channel(CHANNEL_ID)
    await channel.send("✅ GitHub Actions からのテスト投稿です")
    await client.close()

client.run(TOKEN)
