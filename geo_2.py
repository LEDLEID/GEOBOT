import discord
import re
import json
import os
import matplotlib.pyplot as plt
import io
import matplotlib.font_manager as fm
from datetime import datetime, timezone, timedelta

jp_font = fm.FontProperties(fname="C:\\Windows\\Fonts\\msgothic.ttc")
plt.rcParams["font.family"] = jp_font.get_name()

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

    # ---------- データ登録（!Result:xxx-xxx-xxx[,timestamp]） ----------
    if content.startswith('!Result:'):
        try:
            body = content[len('!Result:'):]
            if ',' in body:
                score_part, timestamp_part = body.split(',', 1)
                timestamp = timestamp_part.strip()
                
                # 期待形式: YYYY-MM-DDTHH:MM:SS
                datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')  # バリデーション用
                # 保存時は JST を仮定した文字列のまま扱う（UTC変換などは不要）
            else:
                score_part = body
                timestamp = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')

            match = re.match(r'^(\d+)-(\d+)-(\d+)$', score_part.strip())
            if not match:
                await message.channel.send("❌ 入力形式が不正です。例: `!Result:1000-1000-1000[,2025-07-01T23:40:50]`")
                return

            numbers = list(map(int, match.groups()))

            record = {
                "numbers": numbers,
                "timestamp": timestamp.replace('T', ' ')  # 保存時は JST でスペース区切りに変換
            }

            if username not in results_by_username:
                results_by_username[username] = []

            results_by_username[username].append(record)
            save_results(results_by_username)

            await message.channel.send(f"✅ {username} さんの記録を登録しました: {numbers}（{record['timestamp']}）")

        except Exception as e:
            await message.channel.send(f"⚠️ エラーが発生しました: {e}")
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
                if t1.astimezone(timezone.utc).date() == t2.astimezone(timezone.utc).date():
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
            await message.channel.send("⚠️ 比較できる同日（UTC）の記録が見つかりませんでした。")
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


    # ---------- !Average コマンド ----------
    elif content.lower() == '!average':
        user_records = results_by_username.get(username)
        if not user_records:
            await message.channel.send("📭 あなたの記録が見つかりませんでした。")
            return

        total = [0, 0, 0]
        count = len(user_records)

        for rec in user_records:
            for i in range(3):
                total[i] += rec['numbers'][i]

        avg = [round(total[i] / count, 1) for i in range(3)]
        overall_avg = round(sum(avg) / 3, 1)

        await message.channel.send(
            f"📊 {username} の平均スコア: `{avg[0]} - {avg[1]} - {avg[2]}`\n"
            f"🎯 3つの項目の全体平均: `{overall_avg}`"
        )
        return

    # ---------- !Graph コマンド ----------
    elif content.lower() == '!graph':
        user_records = results_by_username.get(username)
        if not user_records:
            await message.channel.send("📭 あなたの記録が見つかりませんでした。")
            return

        # 全スコアを1つのリストにまとめる
        all_scores = []
        for rec in user_records:
            all_scores.extend(rec['numbers'])

        if not all_scores:
            await message.channel.send("📉 ヒストグラムを描くデータがありません。")
            return

        # 階級（bin）を500刻みに設定
        min_score = min(all_scores)
        max_score = max(all_scores)
        bin_start = (min_score // 500) * 500
        bin_end = ((max_score // 500) + 1) * 500 + 1
        bins = list(range(bin_start, bin_end, 500))

        # 平均スコアを計算
        avg_score = sum(all_scores) / len(all_scores)

        # ヒストグラム描画
        plt.figure(figsize=(8, 5))
        counts, bins_out, patches = plt.hist(all_scores, bins=bins, edgecolor='black', color='skyblue')

        # 平均スコア線（赤い破線）
        plt.axvline(avg_score, color='red', linestyle='dashed', linewidth=2, label=f'平均: {avg_score:.1f}')

        # 各棒グラフの上に数値を表示
        for count, patch in zip(counts, patches):
            if count > 0:
                x = patch.get_x() + patch.get_width() / 2
                y = patch.get_height()
                plt.text(x, y, f'{int(count)}', ha='center', va='bottom', fontsize=10)

        # グラフ装飾
        plt.title(f"{username} のスコアヒストグラム")
        plt.xlabel("スコア")
        plt.ylabel("出現回数")
        plt.grid(axis='y')
        plt.legend()

        # 画像をバッファに保存
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        # Discordに画像送信
        await message.channel.send(file=discord.File(fp=buf, filename='histogram.png'))
        return





client.run(TOKEN)