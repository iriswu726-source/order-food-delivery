"""Telegram 指令處理。"""

from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from .parsing import ParseError, parse_item
from .platforms import PLATFORMS, is_platform_url, resolve_platform
from .storage import Session, Storage, StorageError
from .summary import build_summary, build_user_items, item_line, session_header

HELP_TEXT = """<b>🍱 群組團購點餐 Bot</b>

<b>團主</b>
/neworder 平台 餐廳名稱 [連結] — 開團
　例：/neworder foodpanda 八方雲集 https://www.foodpanda.com.tw/...
　平台可填 foodpanda / fp / ubereats / ue
　連結建議貼平台「團體訂單」的分享連結
/close — 收單並產生彙整
/reopen — 重新開放點餐
/cancel — 取消這次團購

<b>所有人</b>
/add 品項 [$價格] [x數量] [#備註] — 點餐
　例：/add 招牌鍋貼 $6 x10 #要辣
/my — 查看自己的點餐
/remove 編號 — 刪除自己的品項（團主可刪任何人的）
/clear — 清空自己的點餐
/list — 查看目前彙整

ℹ️ foodpanda / Uber Eats 沒有開放消費者下單 API，
收單後請團主依彙整在平台上下單付款（或使用平台的團體訂單功能）。"""


def storage(context: ContextTypes.DEFAULT_TYPE) -> Storage:
    return context.application.bot_data["storage"]


def display_name(user: User) -> str:
    return user.full_name or user.username or str(user.id)


def platform_keyboard(session: Session) -> InlineKeyboardMarkup:
    platform = PLATFORMS[session.platform]
    url = platform.link_for(session.restaurant, session.url)
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(f"🔗 在 {platform.name} 開啟", url=url)]]
    )


async def reply(update: Update, text: str, **kwargs) -> None:
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, **kwargs
    )


async def require_session(update: Update, context) -> Session | None:
    session = storage(context).current_session(update.effective_chat.id)
    if session is None:
        await reply(update, "目前沒有進行中的團購單，請先用 /neworder 開團")
    return session


async def is_organizer(update: Update, context, session: Session) -> bool:
    user = update.effective_user
    if user.id == session.organizer_id:
        return True
    # 群組管理員也可以管理團購單
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("creator", "administrator")
    return False


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, HELP_TEXT)


async def new_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) < 2:
        await reply(update, "用法：/neworder 平台 餐廳名稱 [連結]\n例：/neworder ue 麥當勞")
        return

    platform = resolve_platform(args[0])
    if platform is None:
        await reply(update, "不支援的平台，請填 foodpanda 或 ubereats")
        return

    rest = args[1:]
    url = None
    if rest[-1].startswith(("http://", "https://")):
        url = rest.pop()
        if not is_platform_url(platform, url):
            await reply(update, f"連結看起來不是 {platform.name} 的網址，請確認後再試一次")
            return
    if not rest:
        await reply(update, "請輸入餐廳名稱")
        return

    user = update.effective_user
    try:
        session = storage(context).open_session(
            chat_id=update.effective_chat.id,
            platform=platform.key,
            restaurant=" ".join(rest),
            url=url,
            organizer_id=user.id,
            organizer_name=display_name(user),
        )
    except StorageError as exc:
        await reply(update, f"{exc}，請先 /close 或 /cancel")
        return

    await reply(
        update,
        session_header(session)
        + "\n\n開團囉！大家用 /add 品項 $價格 x數量 #備註 點餐\n例：/add 雞腿便當 $120 x1 #飯少",
        reply_markup=platform_keyboard(session),
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    try:
        parsed = parse_item(" ".join(context.args or []))
    except ParseError as exc:
        await reply(update, str(exc))
        return

    user = update.effective_user
    item = storage(context).add_item(
        session_id=session.id,
        user_id=user.id,
        user_name=display_name(user),
        name=parsed.name,
        quantity=parsed.quantity,
        unit_price=parsed.unit_price,
        note=parsed.note,
    )
    await reply(update, f"✅ 已加入 [{item.id}]：{item_line(item)}")


async def my_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    items = storage(context).items(session.id, update.effective_user.id)
    await reply(update, build_user_items(items))


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    args = context.args or []
    if len(args) != 1 or not args[0].isdigit():
        await reply(update, "用法：/remove 編號（用 /my 查看編號）")
        return
    owner_only = None if await is_organizer(update, context, session) else update.effective_user.id
    if storage(context).remove_item(session.id, int(args[0]), owner_only):
        await reply(update, f"🗑 已刪除品項 [{args[0]}]")
    else:
        await reply(update, "找不到這個品項，或不是你點的")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    count = storage(context).clear_user_items(session.id, update.effective_user.id)
    await reply(update, f"🗑 已清除你的 {count} 個品項")


async def list_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    session = storage(context).current_session(chat_id) or storage(context).last_session(chat_id)
    if session is None:
        await reply(update, "這個群組還沒有團購單，用 /neworder 開團")
        return
    items = storage(context).items(session.id)
    await reply(update, build_summary(session, items), reply_markup=platform_keyboard(session))


async def close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    if not await is_organizer(update, context, session):
        await reply(update, "只有團主或群組管理員可以收單")
        return
    storage(context).set_status(session.id, "closed")
    session = storage(context).get_session(session.id)
    items = storage(context).items(session.id)
    await reply(
        update,
        build_summary(session, items)
        + "\n\n👉 團主請點下方按鈕到平台下單，需要調整可用 /reopen 重新開放",
        reply_markup=platform_keyboard(session),
    )


async def reopen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = storage(context).last_session(update.effective_chat.id)
    if session is None or session.status != "closed":
        await reply(update, "沒有可以重新開放的團購單")
        return
    if not await is_organizer(update, context, session):
        await reply(update, "只有團主或群組管理員可以重新開放")
        return
    storage(context).reopen(session.id)
    await reply(update, "🟢 已重新開放點餐")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = await require_session(update, context)
    if session is None:
        return
    if not await is_organizer(update, context, session):
        await reply(update, "只有團主或群組管理員可以取消團購")
        return
    storage(context).set_status(session.id, "cancelled")
    await reply(update, f"❌ 已取消「{escape(session.restaurant)}」的團購")


def register(app: Application) -> None:
    app.add_handler(CommandHandler(["start", "help"], help_cmd))
    app.add_handler(CommandHandler(["neworder", "open"], new_order))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("my", my_items))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("list", list_items))
    app.add_handler(CommandHandler("close", close))
    app.add_handler(CommandHandler("reopen", reopen))
    app.add_handler(CommandHandler("cancel", cancel))
