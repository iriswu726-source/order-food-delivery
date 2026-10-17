"""啟動 bot：python -m bot.main"""

import logging
import os

from telegram.ext import Application

from .handlers import register
from .storage import Storage


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
    )
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("請設定環境變數 TELEGRAM_BOT_TOKEN")

    app = Application.builder().token(token).build()
    app.bot_data["storage"] = Storage(os.environ.get("DB_PATH", "orders.db"))
    register(app)
    app.run_polling()


if __name__ == "__main__":
    main()
