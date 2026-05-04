import os
import discord

# ===== 環境変数 =====
DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
SERVER_ID = int(os.environ["DISCORD_SERVER_ID"])

MUSIC_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_MUSIC_COMMITEE"])
SCORE_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_SCORE"])
PR_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_PR"])
IT_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_IT"])
CARRIER_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_CARRIER"])
CAMP_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_CAMP"])
OTSUCHI_ROLE_ID = int(os.environ["DISCORD_ROLE_ID_OTSUCHI"])

# ===== 抽出したいロールID =====
TARGET_ROLE_IDS = [
    MUSIC_ROLE_ID,  # 音楽委員
    SCORE_ROLE_ID,  # 楽譜係
    PR_ROLE_ID,     # 広報係
    IT_ROLE_ID,     # IT係
    CARRIER_ROLE_ID,# 運び屋さん
    CAMP_ROLE_ID,   # 合宿係
    OTSUCHI_ROLE_ID # 大槌PR係
]

# ===== Intent設定 =====
intents = discord.Intents.default()
intents.members = True  # メンバー情報取得に必須

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    guild = client.get_guild(SERVER_ID)
    if guild is None:
        print("Guild not found")
        await client.close()
        return

    # ===== ロール取得 =====
    roles = []
    for rid in TARGET_ROLE_IDS:
        role = guild.get_role(rid)
        if role is None:
            print(f"[WARN] role not found: {rid}")
            continue
        roles.append(role)

    if not roles:
        print("No valid roles found")
        await client.close()
        return

    # ===== メンバー集約（重複排除）=====
    members_set = set()

    for role in roles:
        print(f"\n■ Role: {role.name} ({role.id})")

        if not role.members:
            print("  (no members)")
            continue

        for member in role.members:
            members_set.add(member)

    # ===== 結果出力 =====
    print("\n===== Combined Member List (deduplicated) =====")

    if not members_set:
        print("No members found")
    else:
        for m in members_set:
            print(f"- {m.display_name} ({m.id})")

    print("\nDone")

    await client.close()


client.run(DISCORD_TOKEN)