'''
[Release Note]
2026/X/XX version 1 created by M.Ishida
First Release Version
'''

import os
import ssl
from datetime import date, timedelta

import asyncpg
import discord

from collections import defaultdict

# ========= Discord =========
intents = discord.Intents.default()
client = discord.Client(intents=intents)

DISCORD_TOKEN = os.environ["DISCORD_BOT_TOKEN_SCHEDULE_MANAGER"]
EVERYONE_ID = os.environ["DISCORD_EVERYONE"]

CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID_SCHEDULE"])

ATTENDING = "<:syusseki:1244649880576720977>"
ABSENT = "<:kesseki:1244642454745907384>"
LATE = "<:chikoku:1244649936612626472>"
LEAVINGEARLY = "<:soutai:1244642518197600336>"
TBD = "<:mitei:1244642545221369971>"

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
        timeout=10,
    )


@client.event
async def on_ready():
    await process_schedule()
    await client.close()


async def process_schedule():
    today = date.today()
    limit_date_1m = today + timedelta(days=30)
    limit_date_2w = today + timedelta(days=14)
    limit_date_1w = today + timedelta(days=7)
    limit_date_2d = today + timedelta(days=2)

    conn = await get_db_conn()

    # ==============================
    # 1ヶ月前のスレッド作成
    # ==============================
    try:
        rows = await conn.fetch(
            """
            SELECT
                id,
                practice_date,
                start_time,
                end_time,
                place
            FROM schedule
            WHERE announce_1m = FALSE
              AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_1m
        )

        if not rows:
            print("通知対象なし")
        
        # ==============================
        # 出欠依頼
        # ==============================
        for r in rows:
            # 秒を除外した時刻フォーマット
            start_str = r["start_time"].strftime("%H:%M")
            end_str = r["end_time"].strftime("%H:%M")

            channel = await client.fetch_channel(CHANNEL_ID)

            thread_name = f"{r['practice_date'].month}/{r['practice_date'].day}@{r['place']}"

            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread
            )

            thread_id = thread.id

            message = (
                f"<@&{EVERYONE_ID}>\n"
                f"📢 **出欠の入力をお願いします**\n\n"
                f"🗓 日付：**{r['practice_date']}**\n"
                f"⏰ 時間：**{start_str}〜{end_str}**\n"
                f"📍 場所：**{r['place']}**\n\n"
                f"※ 練習日まで1ヶ月となりました。\n"
                f"{ATTENDING} {ABSENT} {LATE} {LEAVINGEARLY} {TBD}のどれかをこのメッセージに押してください"
            )

            msg = await thread.send(message)
           
            await conn.execute(
                """
                UPDATE schedule
                SET announce_1m = TRUE,
                    thread_id = $2,
                    message_id = $3
                WHERE id = $1
                """,
                r["id"],
                str(thread_id),
                str(msg.id)
            )

            print(f"通知・更新完了 id={r['id']}")
    
    finally:
        await conn.close()

    # ==============================
    # 2週間前のリマインド
    # ==============================
    try:
        conn = await get_db_conn()

        rows = await conn.fetch(
            """
            SELECT
                id,
                practice_date,
                start_time,
                end_time,
                place,
                thread_id,
                message_id
            FROM schedule
            WHERE announce_2w = FALSE
            AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_2w
        )

        if not rows:
            print("通知対象なし")

        # ==============================
        # メッセージ送付
        # ==============================
        for r in rows:
            thread_id = int(r["thread_id"])

            try:
                # スレッド取得
                thread = await client.fetch_channel(thread_id)

                # 最初のメッセージ取得
                starter = await thread.fetch_message(int(r["message_id"]))

                # リマインドメッセージ
                remind_message = (
                    f"<@&{EVERYONE_ID}>\n"
                    f"📢 **出欠のリマインドです**\n\n"
                    f"※ 練習日まで2週間です。\n"
                    f"未回答の方は元メッセージにリアクションをお願いします！\n"
                    f"⚠️本メッセージにリアクションしても出欠には反映されません⚠️"
                )

                # 親メッセージに返信
                await starter.reply(remind_message)

                # DB更新
                await conn.execute(
                    """
                    UPDATE schedule
                    SET announce_2w = TRUE
                    WHERE id = $1
                    """,
                    r["id"]
                )

                print(f"リマインド送信完了 id={r['id']}")

            except Exception as e:
                print(f"エラー id={r['id']} : {e}")

    finally:
        await conn.close()

    # ==============================
    # 1週間前の出席者リスト作成
    # ==============================
    
    try:
        conn = await get_db_conn()

        rows = await conn.fetch(
            """
            SELECT
                id,
                practice_date,
                thread_id,
                message_id
            FROM schedule
            WHERE announce_1w_2 = FALSE
            AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_1w
        )

        if not rows:
            print("通知対象なし")

        for r in rows:
            try:
                thread = await client.fetch_channel(int(r["thread_id"]))
                msg = await thread.fetch_message(int(r["message_id"]))

                # ステータスごとにユーザーIDを格納
                status_users = {
                    ATTENDING: [],
                    LATE: [],
                    LEAVINGEARLY: [],
                }

                # ==============================
                # リアクションからユーザー取得
                # ==============================
                for reaction in msg.reactions:
                    users = []
                    
                    emoji = str(reaction.emoji)

                    if emoji not in status_users:
                        continue

                    async for user in reaction.users(limit=None):
                        if user.bot:
                            continue
                        users.append(str(user.id))

                    status_users[emoji] = users

                # ==============================
                # Supabaseから名前取得
                # ==============================
                all_user_ids = list(set(
                    uid for users in status_users.values() for uid in users
                ))

                user_map = {}

                if all_user_ids:
                    records = await conn.fetch(
                        """
                        SELECT user_id, display_name, instrument
                        FROM member
                        WHERE user_id = ANY($1)
                        """,
                        all_user_ids
                    )

                    user_map = {
                        r["user_id"]: {
                            "name": r["display_name"],
                            "instrument": r["instrument"]
                        }
                        for r in records
                    }

                # ==============================
                # グルーピング
                # ==============================
                instrument_map = defaultdict(list)

                status_users[ATTENDING] = [x for x in status_users[ATTENDING] if x not in status_users[LATE]]
                status_users[ATTENDING] = [x for x in status_users[ATTENDING] if x not in status_users[LEAVINGEARLY]]

                all_attendee = status_users[ATTENDING] + status_users[LATE] + status_users[LEAVINGEARLY]

                for uid in all_attendee:
                    user = user_map.get(uid)

                    if user:
                        name = user["name"]
                        inst = user["instrument"]
                    else:
                        name = f"<@{uid}>"
                        inst = "不明"

                    # 遅刻・早退チェック
                    suffix = ""
                    suffix_list = []

                    if uid in status_users[LATE]:
                        suffix_list.append("遅刻")
                    if uid in status_users[LEAVINGEARLY]:
                        suffix_list.append("早退")

                    suffix = f"※{'・'.join(suffix_list)}" if suffix_list else ""
                    instrument_map[inst].append(name + suffix)

                # ==============================
                # 表示用整形
                # ==============================

                instrument_order = [
                    "Fl", "Ob", "Fg", "Cl", "B.Cl",
                    "A.Sax", "T.Sax", "B.Sax",
                    "Trp", "Hr", "Trb", "Eu", "Tu",
                    "Cb", "Perc"
                ]

                lines = []

                for inst in instrument_order:
                    members = instrument_map.get(inst, [])
                    count = len(members)

                    if members:
                        line = f"{inst}({count}) " + "、".join(members)
                    else:
                        line = f"{inst}(0) -"

                    lines.append(line)

                header = (
                    f"<@&{EVERYONE_ID}>\n"
                    "📢 **現在の出欠状況です**\n"
                )
                footer = (
                    "\n\n⚠️ **出欠変更時のお願い**\n"
                    "変更がある場合は、本スレッド最上部のメッセージに押したスタンプを更新してください"
                )
                message_text = header + "\n".join(lines) + footer
                
                await msg.reply(message_text)

                # DB更新
                await conn.execute(
                    """
                    UPDATE schedule
                    SET announce_1w_2 = TRUE
                    WHERE id = $1
                    """,
                    r["id"]
                )

                print(f"出席者リスト作成完了 id={r['id']}")

            except Exception as e:
                print(f"エラー id={r['id']} : {e}")

    finally:
        await conn.close()

    # ==============================
    # 2日前の出欠更新＆出席者リスト作成
    # ==============================

    try:
        conn = await get_db_conn()

        rows = await conn.fetch(
            """
            SELECT
                id,
                practice_date,
                thread_id,
                message_id
            FROM schedule
            WHERE announce_2d = FALSE
            AND practice_date BETWEEN $1 AND $2
            """,
            today,
            limit_date_2d
        )

        if not rows:
            print("通知対象なし")

        for r in rows:
            try:
                thread = await client.fetch_channel(int(r["thread_id"]))
                msg = await thread.fetch_message(int(r["message_id"]))

                # ステータスごとにユーザーIDを格納
                status_users = {
                    ATTENDING: [],
                    LATE: [],
                    LEAVINGEARLY: [],
                }

                # ==============================
                # リアクションからユーザー取得
                # ==============================
                for reaction in msg.reactions:
                    users = []
                    
                    emoji = str(reaction.emoji)

                    if emoji not in status_users:
                        continue

                    async for user in reaction.users(limit=None):
                        if user.bot:
                            continue
                        users.append(str(user.id))

                    status_users[emoji] = users

                # ==============================
                # Supabaseから名前取得
                # ==============================
                all_user_ids = list(set(
                    uid for users in status_users.values() for uid in users
                ))

                user_map = {}

                if all_user_ids:
                    records = await conn.fetch(
                        """
                        SELECT user_id, display_name, instrument
                        FROM member
                        WHERE user_id = ANY($1)
                        """,
                        all_user_ids
                    )

                    user_map = {
                        r["user_id"]: {
                            "name": r["display_name"],
                            "instrument": r["instrument"]
                        }
                        for r in records
                    }

                # ==============================
                # グルーピング
                # ==============================
                instrument_map = defaultdict(list)

                status_users[ATTENDING] = [x for x in status_users[ATTENDING] if x not in status_users[LATE]]
                status_users[ATTENDING] = [x for x in status_users[ATTENDING] if x not in status_users[LEAVINGEARLY]]

                all_attendee = status_users[ATTENDING] + status_users[LATE] + status_users[LEAVINGEARLY]

                for uid in all_attendee:
                    user = user_map.get(uid)

                    if user:
                        name = user["name"]
                        inst = user["instrument"]
                    else:
                        name = f"<@{uid}>"
                        inst = "不明"

                    # 遅刻・早退チェック
                    suffix = ""
                    suffix_list = []

                    if uid in status_users[LATE]:
                        suffix_list.append("遅刻")
                    if uid in status_users[LEAVINGEARLY]:
                        suffix_list.append("早退")

                    suffix = f"※{'・'.join(suffix_list)}" if suffix_list else ""
                    instrument_map[inst].append(name + suffix)

                # ==============================
                # 表示用整形
                # ==============================

                instrument_order = [
                    "Fl", "Ob", "Fg", "Cl", "B.Cl",
                    "A.Sax", "T.Sax", "B.Sax",
                    "Trp", "Hr", "Trb", "Eu", "Tu",
                    "Cb", "Perc"
                ]

                lines = []

                for inst in instrument_order:
                    members = instrument_map.get(inst, [])
                    count = len(members)

                    if members:
                        line = f"{inst}({count}) " + "、".join(members)
                    else:
                        line = f"{inst}(0) -"

                    lines.append(line)

                header = (
                    f"<@&{EVERYONE_ID}>\n"
                    "📢 **確定版出欠です**\n"
                )
                footer = (
                    "\n\n⚠️ **出欠変更時のお願い**\n"
                    "以後の変更は本スレッドにその旨を投稿してください。"
                )
                message_text = header + "\n".join(lines) + footer
                
                await msg.reply(message_text)

                # DB更新
                await conn.execute(
                    """
                    UPDATE schedule
                    SET announce_2d = TRUE
                    WHERE id = $1
                    """,
                    r["id"]
                )

                print(f"出席者リスト作成完了 id={r['id']}")

            except Exception as e:
                print(f"エラー id={r['id']} : {e}")

    finally:
        await conn.close()   


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
