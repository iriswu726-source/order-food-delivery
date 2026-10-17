"""解析 /add 指令的品項文字。

格式：<品項名稱> [$價格] [x數量] [#備註]
例如：
    雞腿便當 $120 x2 #不要辣
    珍珠奶茶 55 半糖少冰
"""

import re
from dataclasses import dataclass

QTY_RE = re.compile(r"^[xX×*](\d+)$|^(\d+)[份個杯碗]$")
PRICE_RE = re.compile(r"^\$?(\d+(?:\.\d+)?)元?$")
MAX_QTY = 99


class ParseError(ValueError):
    pass


@dataclass
class ParsedItem:
    name: str
    quantity: int = 1
    unit_price: float | None = None
    note: str = ""


def parse_item(text: str) -> ParsedItem:
    text = text.strip()
    hash_note = ""
    if "#" in text:
        text, hash_note = text.split("#", 1)

    name_parts: list[str] = []
    note_parts: list[str] = []
    quantity: int | None = None
    price: float | None = None

    for token in text.split():
        qty_match = QTY_RE.match(token)
        if qty_match and quantity is None and name_parts:
            quantity = int(qty_match.group(1) or qty_match.group(2))
            continue
        price_match = PRICE_RE.match(token)
        # 第一個 token 一定是品名的一部分（避免「7up」這類被當成價格）
        if price_match and price is None and name_parts:
            price = float(price_match.group(1))
            continue
        if price is not None or quantity is not None:
            # 價格/數量之後的文字視為備註，例如「珍珠奶茶 55 半糖少冰」
            note_parts.append(token)
            continue
        name_parts.append(token)

    note_parts.append(hash_note.strip())
    note = " ".join(p for p in note_parts if p)

    if not name_parts:
        raise ParseError("請輸入品項名稱，例如：/add 雞腿便當 $120 x2 #不要辣")

    if quantity is None:
        quantity = 1
    if not 1 <= quantity <= MAX_QTY:
        raise ParseError(f"數量需介於 1 到 {MAX_QTY}")

    return ParsedItem(
        name=" ".join(name_parts),
        quantity=quantity,
        unit_price=price,
        note=note,
    )
