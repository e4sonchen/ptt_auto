import requests
from bs4 import BeautifulSoup
import re
import os
import json
import anthropic

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

CONFIG_FILE = 'config.json'
STATE_FILE = 'state.json'

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[通知] {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})

def analyze_with_claude(title, game):
    if not ANTHROPIC_API_KEY:
        return None
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        f"以下是一篇 PTT 筆電販售文章標題：\n「{title}」\n\n"
        f"請根據標題中的規格資訊，簡短判斷這台電腦是否能順暢執行「{game}」。\n"
        f"回答格式：✅ 可以 或 ❌ 不建議，並用一句話說明原因。"
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()

def get_ptt_posts(board):
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    headers = {'User-Agent': 'Mozilla/5.0', 'cookie': 'over18=1'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        return soup.select('.r-ent')
    except Exception as e:
        print(f"Error fetching {board}: {e}")
        return []

def extract_post_id(post):
    a = post.select_one('a')
    if not a:
        return None
    href = a['href']
    match = re.search(r'(\d+)', href)
    return int(match.group(1)) if match else None

def check_board(board, cfg, state):
    posts = get_ptt_posts(board)
    if not posts:
        return

    last_id = state.get(board)
    new_posts = []

    for post in posts:
        pid = extract_post_id(post)
        if pid is None:
            continue
        if last_id is None or pid > last_id:
            new_posts.append((pid, post))

    if not new_posts:
        print(f"[{board}] 沒有新文章")
        return

    # 更新 state 為最新文章 ID
    max_id = max(pid for pid, _ in new_posts)
    state[board] = max_id

    print(f"[{board}] 發現 {len(new_posts)} 篇新文章")

    for pid, post in new_posts:
        title_el = post.select_one('.title')
        if not title_el:
            continue
        title = title_el.text.strip()
        link = "https://www.ptt.cc" + post.select_one('a')['href'] if post.select_one('a') else ""

        # bicycleshop：關鍵字篩選
        if board == 'bicycleshop':
            for kw in cfg.get('keywords', []):
                if kw.upper() in title.upper():
                    msg = f"【PTT 腳踏車】發現關鍵字「{kw}」！\n{title}\n{link}"
                    print(msg)
                    send_telegram(msg)

        # nb-shopping：價格篩選 + Claude 分析
        elif board == 'nb-shopping':
            min_p = cfg.get('min_price', 3000)
            max_p = cfg.get('max_price', 10000)
            prices = re.findall(r'\d+', title)
            for p in prices:
                if min_p < int(p) <= max_p:
                    claude_result = ""
                    if cfg.get('analyze_with_claude') and cfg.get('game'):
                        result = analyze_with_claude(title, cfg['game'])
                        if result:
                            claude_result = f"\n🤖 Claude 分析：{result}"
                    msg = f"【PTT 筆電】發現低價筆電！\n{title}\n{link}{claude_result}"
                    print(msg)
                    send_telegram(msg)
                    break

def analyze():
    config = load_json(CONFIG_FILE)
    state = load_json(STATE_FILE)

    for board, cfg in config['boards'].items():
        if cfg.get('enabled'):
            check_board(board, cfg, state)

    save_json(STATE_FILE, state)
    print("state.json 已更新")

if __name__ == "__main__":
    analyze()
