import requests
from bs4 import BeautifulSoup
import re
import os

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[通知] {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': message})

def get_ptt_posts(board):
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    headers = {'User-Agent': 'Mozilla/5.0', 'cookie': 'over18=1'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        posts = soup.select('.r-ent')
        return posts[:10]
    except Exception as e:
        print(f"Error fetching {board}: {e}")
        return []

def analyze():
    # 1. 檢查 bicycleshop 版的 XS 尺寸
    print("Checking bicycleshop for XS size...")
    bike_posts = get_ptt_posts("bicycleshop")
    for post in bike_posts:
        title = post.select_one('.title').text.strip()
        link = "https://www.ptt.cc" + post.select_one('a')['href'] if post.select_one('a') else ""
        if 'XS' in title.upper():
            msg = f"【PTT 腳踏車】發現 XS 尺寸！\n{title}\n{link}"
            print(msg)
            send_telegram(msg)

    # 2. 檢查 nb-shopping 的價格
    print("\nChecking nb-shopping for price < 10000...")
    nb_posts = get_ptt_posts("nb-shopping")
    for post in nb_posts:
        title = post.select_one('.title').text.strip()
        link = "https://www.ptt.cc" + post.select_one('a')['href'] if post.select_one('a') else ""

        prices = re.findall(r'\d+', title)
        for p in prices:
            if 3000 < int(p) <= 10000:
                msg = f"【PTT 筆電】發現低價筆電！\n{title}\n{link}"
                print(msg)
                send_telegram(msg)
                break

if __name__ == "__main__":
    analyze()
