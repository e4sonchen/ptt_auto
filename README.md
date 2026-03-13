# PTT 自動監控機器人

自動監控 PTT 版面，發現符合條件的文章立刻推播到 Telegram，並用 AI 判斷筆電是否值得購買。

---

## 工作流程

```
GitHub Actions 定時觸發（每小時）
        ↓
爬取 PTT 版面最新文章列表
        ↓
對比 state.json 的上次紀錄 → 只處理新文章
        ↓
┌─────────────────┬──────────────────────────┐
│   bicycleshop   │       nb-shopping        │
│  關鍵字篩選      │  價格篩選（標題→內文）     │
│  (例：XS)       │  (3,000 ~ 10,000 元)     │
└─────────────────┴──────────────────────────┘
        ↓ 符合條件
   Groq AI 分析筆電規格能否玩指定遊戲
        ↓
  Telegram 推播通知
        ↓
更新 state.json 並 commit 回 GitHub
```

---

## 核心概念

**增量爬蟲（不重複通知）**
每篇文章有唯一的數字 ID，`state.json` 記錄上次看到的最大 ID，下次執行只處理比它更新的文章。

**價格偵測**
先從標題抓價格，找不到才進入文章內文，支援逗號格式（`8,500`）和純數字（`8500`）。

**AI 分析**
找到符合價格的筆電後，把標題和規格送給 Groq AI，判斷能否順暢執行指定遊戲，結果一起附在通知訊息裡。

---

## 使用的 API

| API | 用途 | 費用 |
|-----|------|------|
| PTT Web (`ptt.cc`) | 爬取版面文章 | 免費 |
| Telegram Bot API | 推播通知到手機 | 免費 |
| Groq API (Llama 3) | AI 判斷筆電規格 | 免費額度 |
| GitHub Actions | 定時自動執行腳本 | 免費 |

---

## 設定方式

**1. 複製此 Repository**

**2. 在 GitHub Secrets 加入以下三個變數**
> Settings → Secrets and variables → Actions → New repository secret

| 名稱 | 說明 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（從 @BotFather 取得）|
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |
| `GROQ_API_KEY` | Groq API Key（從 console.groq.com 取得）|

**3. 修改 `config.json` 調整監控條件**

```json
{
  "boards": {
    "bicycleshop": {
      "enabled": true,
      "keywords": ["XS"]
    },
    "nb-shopping": {
      "enabled": true,
      "min_price": 3000,
      "max_price": 10000,
      "analyze_with_claude": true,
      "game": "魔物獵人 崛起"
    }
  }
}
```

**4. 手動觸發測試**
> GitHub → Actions → PTT Monitor → Run workflow

排程預設每小時整點自動執行，可在 `.github/workflows/main.yml` 的 `cron` 修改頻率。

---

## 檔案結構

```
ptt_auto/
├── ptt_monitor.py          # 主程式
├── config.json             # 監控條件設定
├── state.json              # 記錄上次讀取位置（自動更新）
└── .github/workflows/
    └── main.yml            # GitHub Actions 排程設定
```
