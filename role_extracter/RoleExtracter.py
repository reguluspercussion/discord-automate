import os
import discord

# ===== 環境変数 =====
DISCORD_TOKEN= os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
SERVER_ID = int(os.environ["DISCORD_SERVER_ID"])

# ===== Intent設定 =====
intents = discord.Intents.default()
intents.members = True  # ← 必須

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    guild = client.get_guild(SERVER_ID)
    if guild is None:
        print("Guild not found")
        await client.close()
        return

    print("fetching members...")

    members = []
    count = 0

    async for m in guild.fetch_members(limit=None):
        members.append(m)
        count += 1

        if count % 50 == 0:
            print(f"fetched: {count}")

    print(f"total members: {len(members)}")

    print("\n===== Role Member List =====")

    for role in guild.roles:
        print(f"\n■ {role.name}")

        role_members = [m for m in members if role in m.roles]

        if not role_members:
            print("  (no members)")
            continue

        for member in role_members:
            print(f"  - {member.display_name}")

    print("\nDone")

    await client.close()

    # ===== メンバーキャッシュ取得（重要）=====
    await guild.chunk()

    # ===== ここに入れる =====
    print("before fetch")
    async for m in guild.fetch_members(limit=1):
        print("got one member")
        break
    print("after fetch")

    print("\n===== Role Member List =====")

    for role in guild.roles:
        print(f"\n■ {role.name} ({role.id})")

        if len(role.members) == 0:
            print("  (no members)")
            continue

        for member in role.members:
            print(f"  - {member.display_name} ({member.id})")

    print("\n===== Done =====")

    # 一回実行で終了
    await client.close()

client.run(DISCORD_TOKEN)