import requests
from bs4 import BeautifulSoup
import re
import os
import json
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

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

def analyze_with_groq(title, game):
    if not GROQ_API_KEY:
        print("[Groq] 未設定 GROQ_API_KEY，跳過分析")
        return None
    prompt = (
        f"以下是一篇 PTT 筆電販售文章標題：\n「{title}」\n\n"
        f"請根據標題中的規格資訊，用繁體中文簡短判斷這台電腦是否能順暢執行「{game}」。\n"
        f"回答格式：✅ 可以 或 ❌ 不建議，並用一句話說明原因。"
    )
    url = "https://api.groq.com/openai/v1/chat/completions"
    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }
    try:
        res = requests.post(url, json=body, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=15)
        print(f"[Groq] HTTP {res.status_code}")
        data = res.json()
        result = data['choices'][0]['message']['content'].strip()
        print(f"[Groq] 分析完成：{result[:80]}")
        return result
    except Exception as e:
        resp_text = res.text[:300] if 'res' in dir() else '無'
        print(f"[Groq] 分析失敗：{e}，回應：{resp_text}")
        return None

def get_ptt_posts(board):
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'cookie': 'over18=1',
        'Referer': 'https://www.ptt.cc/bbs/index.html',
    }
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            return soup.select('.r-ent')
        except Exception as e:
            print(f"Error fetching {board} (attempt {attempt+1}/3): {e}")
            if attempt < 2:
                import time; time.sleep(3)
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

        # nb-shopping：價格篩選 + AI 分析
        elif board == 'nb-shopping':
            min_p = cfg.get('min_price', 3000)
            max_p = cfg.get('max_price', 10000)
            # 只抓 4~6 位純數字，排除緊接英文字母的型號（如 9750H、4800U、RTX3060）
            prices = re.findall(r'(?<![a-zA-Z\d])(\d{4,6})(?![a-zA-Z\d])', title)
            print(f"  標題：{title}")
            print(f"  抓到數字：{prices}")
            matched = False
            for p in prices:
                if min_p < int(p) <= max_p:
                    matched = True
                    print(f"  價格符合：{p}")
                    ai_result = ""
                    if cfg.get('analyze_with_claude') and cfg.get('game'):
                        result = analyze_with_groq(title, cfg['game'])
                        if result:
                            ai_result = f"\n🤖 AI 分析：{result}"
                    msg = f"【PTT 筆電】發現低價筆電！\n{title}\n{link}{ai_result}"
                    print(msg)
                    send_telegram(msg)
                    break
            if not matched:
                print(f"  價格不符（需 {min_p}~{max_p}）")

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
