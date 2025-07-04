import discord
import re
import json
import os
from datetime import datetime, timezone, timedelta

with open('TOKEN.txt', 'r') as f:
    TOKEN = f.read().strip()

DATA_FILE = 'results.json'
JST = timezone(timedelta(hours=9))
TIME_WINDOW = timedelta(hours=6)

# --- データの読み書き（usernameをキー） ---
def load_results():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_results(results):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

results_by_username = load_results()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Bot logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author.bot:
        return

    username = message.author.name
    content = message.content.strip()

    # ---------- データ登録 ----------
    match = re.match(r'^!Result:(\d+)-(\d+)-(\d+)$', content)
    if match:
        numbers = list(map(int, match.groups()))
        timestamp = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')

        record = {
            "numbers": numbers,
            "timestamp": timestamp
        }

        if username not in results_by_username:
            results_by_username[username] = []

        results_by_username[username].append(record)
        save_results(results_by_username)

        await message.channel.send(f"✅ {username} さんの記録を追加しました: {numbers}（{timestamp}）")
        return

    # ---------- !list コマンド ----------
    if content.lower() == '!list':
        user_records = results_by_username.get(username)
        if user_records:
            msg_lines = [f"📋 {username} の記録（{len(user_records)}件）:"]
            for i, r in enumerate(user_records, 1):
                msg_lines.append(f"{i}. {r['numbers']} | {r['timestamp']}")
            await message.channel.send('\n'.join(msg_lines))
        else:
            await message.channel.send("📭 あなたの記録はまだありません。")
        return

    # ---------- 勝敗比較（!user1_user2） ----------
    match_vs = re.match(r'^!(\w+)!([\w]+)$', content)
    if match_vs:
        user1, user2 = match_vs.groups()

        data1 = results_by_username.get(user1)
        data2 = results_by_username.get(user2)

        if not data1 or not data2:
            await message.channel.send("❌ 一方または両方のユーザーに記録がありません。")
            return

        def parse_time(t): return datetime.strptime(t, '%Y-%m-%d %H:%M:%S').replace(tzinfo=JST)

        total_win, total_draw, total_lose = 0, 0, 0
        match_count = 0
        matched_times = []

        for r1 in data1:
            t1 = parse_time(r1['timestamp'])
            for r2 in data2:
                t2 = parse_time(r2['timestamp'])
                if abs(t1 - t2) <= TIME_WINDOW:
                    win, draw, lose = 0, 0, 0
                    for n1, n2 in zip(r1['numbers'], r2['numbers']):
                        if n1 > n2:
                            win += 1
                        elif n1 < n2:
                            lose += 1
                        else:
                            draw += 1
                    total_win += win
                    total_draw += draw
                    total_lose += lose
                    match_count += 1
                    matched_times.append((r1['timestamp'], r2['timestamp']))

        if match_count == 0:
            await message.channel.send("⚠️ 比較できる同時刻（±6時間）の記録が見つかりませんでした。")
        else:
            result_msg = f"🔍 `{user1}` vs `{user2}` の合計結果: **{total_win}-{total_draw}-{total_lose}**"
            result_msg += f"\n🔁 比較回数: {match_count} 回"
            await message.channel.send(result_msg)

    # ---------- !Redo コマンド ----------
    elif content.lower() == '!redo':
        user_records = results_by_username.get(username)
        if user_records and len(user_records) > 0:
            removed = user_records.pop()
            save_results(results_by_username)
            await message.channel.send(f"🗑️ 最新の記録を削除しました: {removed['numbers']} ({removed['timestamp']})")
        else:
            await message.channel.send("📭 削除できる記録が見つかりませんでした。")
        return


client.run(TOKEN)