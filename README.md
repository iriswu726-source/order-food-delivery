# Telegram 群組團購點餐 Bot（foodpanda / Uber Eats）

在 Telegram 群組裡開團、讓大家各自點餐，收單後自動彙整品項與每人金額，
並附上 foodpanda / Uber Eats 的連結讓團主直接到平台下單。

## 關於「直接串接下單」

foodpanda（Delivery Hero）和 Uber Eats **都沒有開放「以消費者身分下單」的公開 API**：

- Uber Eats 的 API 是給餐廳（Marketplace / Menu / Order API，管理自家菜單與接單）
  和 Uber Direct（商家叫外送員），無法替一般使用者在別家餐廳下單。
- foodpanda 的 Partner API 也只給合作店家使用。
- 用爬蟲或瀏覽器自動化模擬登入下單違反兩個平台的服務條款，
  還要把帳號密碼與付款資訊交給 bot，帳號有被停用的風險，所以本專案不這麼做。

因此 bot 的做法是：**群組內收單＋彙整 → 團主一鍵開啟平台 → 照彙整下單付款**。
建議團主先在平台 App 建立「團體訂單 / Group Order」，把分享連結貼進 `/neworder`，
按鈕就會直接帶大家到同一張團體訂單。

如果之後平台開放對應 API（或你有合作店家權限），可以在 `bot/platforms.py`
加上下單實作，在 `/close` 時呼叫。

## 指令

| 指令 | 說明 |
| --- | --- |
| `/neworder 平台 餐廳名稱 [連結]` | 開團。平台：`foodpanda`/`fp`、`ubereats`/`ue` |
| `/add 品項 [$價格] [x數量] [#備註]` | 點餐，例：`/add 雞腿便當 $120 x2 #不要辣` |
| `/my` | 查看自己的點餐與編號 |
| `/remove 編號` | 刪除自己的品項（團主/管理員可刪任何人的） |
| `/clear` | 清空自己的點餐 |
| `/list` | 查看目前彙整 |
| `/close` | 收單，輸出「品項彙整」與「每人明細」＋平台按鈕 |
| `/reopen` | 收單後重新開放 |
| `/cancel` | 取消團購 |

`/add` 也接受比較口語的寫法：`/add 珍珠奶茶 55 半糖少冰`、`/add 鍋貼 6元 10個`。

團主、群組管理員才能 `/close`、`/reopen`、`/cancel`。每個群組同時只會有一張進行中的團購單。

## 範例

```
/neworder fp 八方雲集 https://www.foodpanda.com.tw/restaurant/xxxx
/add 招牌鍋貼 $6 x10 #要辣
/add 酸辣湯 $35
/close
```

收單後輸出：

```
🍱 八方雲集（foodpanda）
團主：Amy　🔒 已收單

📋 品項彙整（照這個在平台下單）
• 招牌鍋貼 ×15（要辣）
• 酸辣湯 ×1

👥 每人明細
Amy — $60
  招牌鍋貼 ×10 $60（要辣）
Bob — $65
  招牌鍋貼 ×5 $30（要辣）
  酸辣湯 ×1 $35

共 2 人、16 份，餐點小計 $125
[🔗 在 foodpanda 開啟]
```

## 安裝與執行

1. 找 [@BotFather](https://t.me/BotFather) 建立 bot，取得 token。
2. 若要讓 bot 在群組收到 `/add 品項` 這類指令，預設設定即可（指令訊息不受 privacy mode 影響）。
3. 執行：

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=你的token
python -m bot.main
```

或用 Docker：

```bash
docker build -t order-bot .
docker run -d -e TELEGRAM_BOT_TOKEN=你的token -v order-data:/data order-bot
```

4. 把 bot 加進群組，輸入 `/help`。

## 開發

```bash
pip install -r requirements-dev.txt
pytest
```

程式結構：

- `bot/handlers.py` — Telegram 指令
- `bot/parsing.py` — 解析 `/add` 文字
- `bot/storage.py` — SQLite 儲存
- `bot/summary.py` — 彙整訊息
- `bot/platforms.py` — 平台設定與連結
