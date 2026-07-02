# role_report.py
import os
from datetime import datetime, timedelta, timezone
import asyncpg
import discord

DISCORD_TOKEN=os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
SERVER_ID=int(os.environ["DISCORD_SERVER_ID"])
THREAD_ID=os.environ["DISCORD_THREAD_ID_ROLE_LIST"]

ROLE_ENV_NAMES=[
"DISCORD_ROLE_ID_MUSIC_COMMITEE",
"DISCORD_ROLE_ID_SCORE",
"DISCORD_ROLE_ID_PR",
"DISCORD_ROLE_ID_IT",
"DISCORD_ROLE_ID_CARRIER",
"DISCORD_ROLE_ID_EVENT",
"DISCORD_ROLE_ID_OTSUCHI",
]
TARGET_ROLE_IDS=[int(os.environ[x]) for x in ROLE_ENV_NAMES]

DB_HOST=os.environ["DB_HOST"]
DB_PORT=int(os.environ["DB_PORT"])
DB_NAME=os.environ["DB_DATABASE"]
DB_USER=os.environ["DB_USER"]
DB_PASSWORD=os.environ["DB_PASSWORD"]

intents=discord.Intents.default()
intents.members=True
client=discord.Client(intents=intents)

@client.event
async def on_ready():
    guild=client.get_guild(SERVER_ID)
    if guild is None:
        print("Guild not found"); await client.close(); return

    conn=await asyncpg.connect(host=DB_HOST,port=DB_PORT,database=DB_NAME,user=DB_USER,password=DB_PASSWORD,ssl="require")
    rows=await conn.fetch("SELECT user_id,inst_id,instrument,display_name FROM member")
    await conn.close()

    member_map={str(r["user_id"]):{"inst_id":r["inst_id"],"name":f'{r["instrument"]} {r["display_name"]}'} for r in rows}

    now = datetime.now()
    lines = [
        f"===== {now.strftime('%Y年%m月%d日')}時点の係メンバー一覧 =====",
        ""
    ]
    for rid in TARGET_ROLE_IDS:
        role=guild.get_role(rid)
        if role is None:
            continue
        lines.append(f"■ {role.name}")
        members=[m for m in role.members if not m.bot]
        members.sort(key=lambda m: member_map.get(str(m.id),{"inst_id":9999})["inst_id"])
        if not members:
            lines.append("  (no members)")
        else:
            for m in members:
                lines.append(f' - {member_map.get(str(m.id),{"name":m.display_name})["name"]}')
        lines.append("")

    message="\n".join(lines)
    print(message)

    thread=guild.get_thread(THREAD_ID)
    if thread is None:
        thread=await client.fetch_channel(THREAD_ID)

    last=None
    async for msg in thread.history(limit=100):
        if msg.author.id==client.user.id:
            last=msg
            break

    should_post = last is None or (datetime.now(timezone.utc)-last.created_at)>=timedelta(days=30)
    
    if should_post:
        await thread.send(message)
        print("Posted.")
    else:
        print("Skipped: latest bot post is within 30 days.")
    
    await client.close()

client.run(DISCORD_TOKEN)
