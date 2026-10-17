"""用假的 Update/Context 走過一次完整的開團→點餐→收單流程。"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot import handlers
from bot.storage import Storage


class Chat:
    def __init__(self):
        self.store = Storage()
        self.replies: list[str] = []
        self.bot = SimpleNamespace(
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status="member"))
        )

    def run(self, handler, user_id, args):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_message=message,
            effective_chat=SimpleNamespace(id=-100, type="supergroup"),
            effective_user=SimpleNamespace(
                id=user_id, full_name=f"user{user_id}", username=None
            ),
        )
        context = SimpleNamespace(
            args=args.split(),
            bot=self.bot,
            application=SimpleNamespace(bot_data={"storage": self.store}),
        )
        asyncio.run(handler(update, context))
        text = message.reply_text.call_args.args[0]
        self.replies.append(text)
        return text


def test_full_flow():
    chat = Chat()
    assert "開團囉" in chat.run(handlers.new_order, 1, "fp 八方雲集 https://www.foodpanda.com.tw/restaurant/x")
    assert "已經有進行中" in chat.run(handlers.new_order, 2, "ue 麥當勞")

    chat.run(handlers.add, 1, "鍋貼 $6 x10 #要辣")
    chat.run(handlers.add, 2, "鍋貼 $6 x5 #要辣")
    chat.run(handlers.add, 2, "酸辣湯 $35")

    assert "只有團主" in chat.run(handlers.close, 2, "")
    summary = chat.run(handlers.close, 1, "")
    assert "鍋貼 ×15（要辣）" in summary
    assert "餐點小計 $125" in summary

    assert "沒有進行中" in chat.run(handlers.add, 2, "雞排")
    assert "重新開放" in chat.run(handlers.reopen, 1, "")
    chat.run(handlers.add, 2, "雞排 $80")


def test_rejects_non_platform_url():
    chat = Chat()
    assert "不是 Uber Eats" in chat.run(handlers.new_order, 1, "ue 麥當勞 https://evil.example.com")
    assert chat.store.current_session(-100) is None


def test_member_cannot_remove_others_item():
    chat = Chat()
    chat.run(handlers.new_order, 1, "ue 麥當勞")
    chat.run(handlers.add, 1, "大麥克")
    item_id = chat.store.items(chat.store.current_session(-100).id)[0].id
    assert "找不到" in chat.run(handlers.remove, 2, str(item_id))
    assert "已刪除" in chat.run(handlers.remove, 1, str(item_id))
