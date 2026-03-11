import requests
from bs4 import BeautifulSoup
import re

def get_ptt_posts(board):
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    headers = {'User-Agent': 'Mozilla/5.0', 'cookie': 'over18=1'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 取得文章列表（排除置底公告）
        posts = soup.select('.r-ent')
        return posts[:10]  # 取前 10 篇確保涵蓋最新 5 篇非公告文章
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
            print(f"【發現目標】{title} \n連結: {link}")

    # 2. 檢查 nb-shopping 的價格
    print("\nChecking nb-shopping for price < 10000...")
    nb_posts = get_ptt_posts("nb-shopping")
    for post in nb_posts:
        title = post.select_one('.title').text.strip()
        link = "https://www.ptt.cc" + post.select_one('a')['href'] if post.select_one('a') else ""
        
        # 使用正規表達式找尋標題中的數字（通常賣家會把價格寫在標題）
        prices = re.findall(r'\d+', title)
        for p in prices:
            if 3000 < int(p) <= 10000:  # 這裡設定 > 3000 是為了過濾掉年份或型號數字
                print(f"【發現低價筆電】{title} \n連結: {link}")
                break

if __name__ == "__main__":
    analyze()