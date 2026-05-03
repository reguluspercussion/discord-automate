# メモ
# 出席者から打楽器のみを抽出するところまで出来ている

import os
import ssl
from datetime import date, timedelta

import asyncpg
import discord

# ========= Discord =========
intents = discord.Intents.default()
client = discord.Client(intents=intents)

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]

ATTENDING = "<:syusseki:1244649880576720977>"
LATE = "<:chikoku:1244649936612626472>"
LEAVINGEARLY = "<:soutai:1244642518197600336>"

# ========= DB =========
async def get_db_conn():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_DATABASE"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        ssl=ssl_ctx,
    )

# ========= メイン処理 =========
@client.event
async def on_ready():
    result = await extract_perc_attendees()
    print("=== Perc出席者 ===")
    print(result)
    await client.close()

async def extract_perc_attendees():
    today = date.today()
    limit_date_5d = today + timedelta(days=5)

    conn = await get_db_conn()

    try:
        # ==============================
        # 対象スケジュール取得
        # ==============================
        rows = await conn.fetch(
            """
            SELECT
                id,
                thread_id,
                message_id
            FROM schedule
            WHERE announce_perc = FALSE
              AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_5d
        )

        if not rows:
            print("対象スケジュールなし")
            return []

        perc_members = []

        # ==============================
        # 各スケジュール処理
        # ==============================
        for r in rows:
            try:
                thread = await client.fetch_channel(int(r["thread_id"]))
                msg = await thread.fetch_message(int(r["message_id"]))

                # ステータス別ユーザー
                status_users = {
                    ATTENDING: [],
                    LATE: [],
                    LEAVINGEARLY: [],
                }

                # ==============================
                # リアクション取得
                # ==============================
                for reaction in msg.reactions:
                    emoji = str(reaction.emoji)

                    if emoji not in status_users:
                        continue

                    async for user in reaction.users(limit=None):
                        if user.bot:
                            continue
                        status_users[emoji].append(str(user.id))

                # ==============================
                # 対象ユーザーIDまとめ
                # ==============================
                all_ids = list(set(
                    uid for users in status_users.values() for uid in users
                ))

                if not all_ids:
                    continue

                # ==============================
                # Percのみ取得
                # ==============================
                records = await conn.fetch(
                    """
                    SELECT user_id, display_name
                    FROM member
                    WHERE user_id = ANY($1)
                      AND instrument = 'Perc'
                    """,
                    all_ids
                )

                for rec in records:
                    uid = rec["user_id"]
                    name = rec["display_name"]

                    status = []

                    if uid in status_users[LATE]:
                        status.append("遅刻")
                    if uid in status_users[LEAVINGEARLY]:
                        status.append("早退")

                    suffix = f"※{'・'.join(status)}" if status else ""

                    perc_members.append(name + suffix)

            except Exception as e:
                print(f"エラー id={r['id']} : {e}")

        # ==============================
        # デバッグ出力
        # ==============================
        print(f"Perc抽出結果: {perc_members}")

        return perc_members

    finally:
        await conn.close()

# ========= 実行 =========
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)