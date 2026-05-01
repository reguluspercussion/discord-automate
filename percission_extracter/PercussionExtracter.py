'''
[Release Note]
2026/X/XX version 1 created by M.Ishida
First Release Version
'''
import re
import discord
from datetime import datetime, timedelta

# ==============================
# メイン処理
# ==============================

async def announce_percussion_if_needed(client, db):
    """
    打楽器運搬アナウンスのメイン処理

    フロー：
    ① 対象スケジュール取得
    ② スレッドから練習予定取得
    ③ 曲目抽出
    ④ Perc出席者抽出
    ⑤ 必要楽器抽出
    ⑥ 投稿
    ⑦ フラグ更新
    """

    schedules = await fetch_target_schedules(db)

    if not schedules:
        return

    for schedule in schedules:
        thread = await fetch_thread(client, schedule["thread_id"])

        # ② 練習予定確認
        practice_msg = await find_practice_message(thread)
        if not practice_msg:
            await notify_no_plan(thread)
            continue

        # ③ 曲目抽出（■練習予定以降のみ）
        songs = extract_songs_from_section(practice_msg.content)
        if not songs:
            await notify_no_plan(thread)
            continue

        # ④ Perc出席者抽出
        perc_members = await extract_perc_attendees(client, schedule["message_id"])
        if not perc_members:
            continue

        # ⑤ 必要楽器抽出
        instruments = await extract_instruments(
            db,
            schedule["concert_id"],
            songs,
            perc_members
        )

        # ⑥ 投稿
        await post_result(thread, schedule, songs, perc_members, instruments)

        # ⑦ フラグ更新
        await mark_announced(db, schedule["id"])


# ==============================
# ① スケジュール取得
# ==============================

async def fetch_target_schedules(db):
    """
    ・練習まで5日未満
    ・announce_perc = false
    のスケジュールを取得
    """
    query = """
    SELECT *
    FROM schedule
    WHERE practice_date < NOW() + INTERVAL '5 days'
      AND announce_perc = false
    """
    return await db.fetch(query)


# ==============================
# ② 練習予定メッセージ取得
# ==============================

async def fetch_thread(client, thread_id):
    """thread_idからスレッド取得"""
    return await client.fetch_channel(thread_id)


async def find_practice_message(thread):
    """
    スレッド内から「■練習予定」を含むメッセージを探す
    """
    async for msg in thread.history(limit=100):
        if "■練習予定" in msg.content:
            return msg
    return None


# ==============================
# ③ 曲目抽出（ここが今回のポイント）
# ==============================

def extract_songs_from_section(content):
    """
    「■練習予定」セクションのみを対象に曲目を抽出

    仕様：
    ・「■練習予定」以降を対象
    ・次の「■」セクションが来たら終了
    ・「・曲名」形式を抽出
    """

    lines = content.splitlines()

    songs = []
    in_section = False

    for line in lines:
        line = line.strip()

        # セクション開始
        if "■練習予定" in line:
            in_section = True
            continue

        # 別セクションに入ったら終了
        if in_section and line.startswith("■"):
            break

        # セクション内のみ処理
        if in_section:
            match = re.match(r"[・\-]\s*(.+)", line)
            if match:
                songs.append(match.group(1).strip())

    return songs


# ==============================
# ④ Perc出席者抽出
# ==============================

async def extract_perc_attendees(client, message_id):
    """
    出欠リアクションからPercメンバーのみ抽出
    ※既存ロジック流用前提
    """

    message = await fetch_message(client, message_id)

    attendees = parse_reactions(message)

    perc_members = [
        m for m in attendees
        if is_percussion_member(m)
    ]

    return perc_members


async def fetch_message(client, message_id):
    """message_idからメッセージ取得（channelは適宜調整）"""
    # 既存実装に合わせて修正
    channel = client.get_channel(YOUR_CHANNEL_ID)
    return await channel.fetch_message(message_id)


# ==============================
# ⑤ 必要楽器抽出
# ==============================

async def extract_instruments(db, concert_id, songs, members):
    """
    ・percussionテーブル参照
    ・曲名一致
    ・メンバ列からtext[]取得
    ・重複排除
    """

    rows = await db.fetch("""
        SELECT *
        FROM percussion
        WHERE concert_id = $1
        ORDER BY concert_id DESC
    """, concert_id)

    instruments = set()

    for song in songs:
        row = next(
            (r for r in rows if normalize(r["song_name"]) == normalize(song)),
            None
        )

        if not row:
            continue

        for member in members:
            if member in row and row[member]:
                instruments.update(row[member])

    return list(instruments)


def normalize(text):
    """曲名の簡易正規化"""
    return text.replace(" ", "").lower()


# ==============================
# ⑥ 投稿
# ==============================

async def post_result(thread, schedule, songs, members, instruments):
    """
    結果をスレッドに投稿
    """

    msg = f"""
■打楽器運搬整理

【日付】
{schedule['practice_date']}

【場所】
{schedule['location']}

【練習曲】
{', '.join(songs)}

【参加者】
{', '.join(members)}

【必要楽器】
{', '.join(instruments)}
"""

    await thread.send(msg)


# ==============================
# ⑦ フラグ更新
# ==============================

async def mark_announced(db, schedule_id):
    """announce_percをtrueに更新"""
    await db.execute("""
        UPDATE schedule
        SET announce_perc = true
        WHERE id = $1
    """, schedule_id)


# ==============================
# 補助（通知）
# ==============================

async def notify_no_plan(thread):
    """練習予定未確定時の通知"""
    await thread.send("練習予定が決まっていません（■練習予定が未記載）")