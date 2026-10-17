"""產生團購單的彙整文字（以 Telegram HTML 格式輸出）。"""

from collections import OrderedDict
from html import escape

from .platforms import PLATFORMS
from .storage import Item, Session


def fmt_money(value: float) -> str:
    return f"${value:,.0f}" if value == int(value) else f"${value:,.2f}"


def item_line(item: Item, with_id: bool = False) -> str:
    parts = []
    if with_id:
        parts.append(f"[{item.id}]")
    parts.append(f"{escape(item.name)} ×{item.quantity}")
    if item.subtotal is not None:
        parts.append(fmt_money(item.subtotal))
    line = " ".join(parts)
    if item.note:
        line += f"（{escape(item.note)}）"
    return line


def session_header(session: Session) -> str:
    platform = PLATFORMS[session.platform]
    status = {"open": "🟢 點餐中", "closed": "🔒 已收單", "cancelled": "❌ 已取消"}
    return (
        f"<b>🍱 {escape(session.restaurant)}</b>（{platform.name}）\n"
        f"團主：{escape(session.organizer_name)}　{status[session.status]}"
    )


def build_summary(session: Session, items: list[Item]) -> str:
    lines = [session_header(session), ""]
    if not items:
        lines.append("目前還沒有人點餐。用 /add 品項 $價格 x數量 #備註 來點餐")
        return "\n".join(lines)

    # 依品項彙整（同名同備註合併），方便團主在平台上照著點
    lines.append("<b>📋 品項彙整（照這個在平台下單）</b>")
    grouped: "OrderedDict[tuple[str, str], list[Item]]" = OrderedDict()
    for item in items:
        grouped.setdefault((item.name, item.note), []).append(item)
    for (name, note), group in grouped.items():
        qty = sum(i.quantity for i in group)
        line = f"• {escape(name)} ×{qty}"
        if note:
            line += f"（{escape(note)}）"
        lines.append(line)

    # 依人彙整，方便收錢
    lines += ["", "<b>👥 每人明細</b>"]
    by_user: "OrderedDict[int, list[Item]]" = OrderedDict()
    for item in items:
        by_user.setdefault(item.user_id, []).append(item)
    for user_items in by_user.values():
        priced = [i.subtotal for i in user_items if i.subtotal is not None]
        total = f" — {fmt_money(sum(priced))}" if priced else ""
        lines.append(f"<b>{escape(user_items[0].user_name)}</b>{total}")
        for item in user_items:
            lines.append("  " + item_line(item))

    total_qty = sum(i.quantity for i in items)
    priced = [i.subtotal for i in items if i.subtotal is not None]
    lines.append("")
    footer = f"共 {len(by_user)} 人、{total_qty} 份"
    if priced:
        footer += f"，餐點小計 {fmt_money(sum(priced))}"
        if len(priced) < len(items):
            footer += "（部分品項未填價格）"
    lines.append(footer)
    lines.append("<i>※ 外送費、服務費與優惠以平台結帳金額為準</i>")
    return "\n".join(lines)


def build_user_items(items: list[Item]) -> str:
    if not items:
        return "你在這張團購單還沒有點任何東西"
    lines = ["<b>你的點餐</b>"] + [item_line(i, with_id=True) for i in items]
    lines.append("\n用 /remove 編號 刪除單一品項，/clear 清空自己的點餐")
    return "\n".join(lines)
