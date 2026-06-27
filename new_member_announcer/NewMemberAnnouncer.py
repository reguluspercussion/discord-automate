"""
[Release Note]
2026/6/27 Version 1 created by M.Ishida
First Release Version

Check Discord members against the Supabase member table.
Notify the staff thread when unregistered members are found.
"""

import os
import ssl
import asyncpg
import discord

# ========= Discord =========
DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
SERVER_ID = int(os.environ["DISCORD_SERVER_ID"])
THREAD_ID = int(os.environ["DISCORD_THREAD_ID_MEMBER_NOTICE"])

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

# ========= Supabase =========
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_NAME = os.environ["DB_DATABASE"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]


@client.event
async def on_ready():

    print("--------------------------------")
    print(f"Logged in as {client.user}")
    print("Start member check")
    print("--------------------------------")

    # =========================
    # Discord Server
    # =========================
    guild = client.get_guild(SERVER_ID)

    if guild is None:
        print("Guild not found.")
        await client.close()
        return

    print(f"Guild : {guild.name}")

    # =========================
    # Discord Members
    # =========================
    print("Fetching Discord members...")

    discord_members = []

    try:
        async for member in guild.fetch_members(limit=None):
            if not member.bot:
                discord_members.append(member)

        print(f"Discord Members : {len(discord_members)}")

    except Exception as e:
        print("Failed to fetch Discord members.")
        print(e)
        await client.close()
        return

    # =========================
    # Supabase
    # =========================
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_DATABASE"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        ssl=ssl_ctx,
        timeout=10,
    )

    rows = await conn.fetch("""
        SELECT user_id
        FROM member
        WHERE user_id IS NOT NULL;
    """)

    registered_ids = {
        int(row["user_id"])
        for row in rows
    }

    print(f"Supabase Members : {len(registered_ids)}")

    # =========================
    # Difference
    # =========================
    unregistered = []

    for member in discord_members:
        if member.id not in registered_ids:
            unregistered.append(member)

    print(f"Unregistered Members : {len(unregistered)}")

    # =========================
    # Notify
    # =========================
    if unregistered:

        thread = await client.fetch_channel(THREAD_ID)

        if isinstance(thread, discord.Thread) and thread.archived:
            print("Unarchiving thread...")
            await thread.edit(archived=False)

        message = (
            "📢 **Supabase未登録メンバーを検知しました。**\n\n"
            "以下のメンバーはDiscordには参加していますが、"
            "Supabase(member)には登録されていません。\n\n"
        )

        for member in unregistered:
            message += (
                f"・{member.mention}\n"
                f"　表示名：{member.display_name}\n"
                f"　ユーザー名：{member.name}\n"
                f"　ID：`{member.id}`\n\n"
            )

        message += (
            "Supabaseへの登録完了後、この通知は表示されなくなります。"
        )

        await thread.send(message)

        print("Notification sent.")

    else:

        print("No unregistered members.")

    # =========================
    # Finish
    # =========================
    await conn.close()

    print("Finished.")

    await client.close()


client.run(DISCORD_TOKEN)