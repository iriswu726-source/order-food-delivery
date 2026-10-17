import pytest

from bot.parsing import ParseError, parse_item


def test_full_format():
    item = parse_item("雞腿便當 $120 x2 #不要辣")
    assert (item.name, item.unit_price, item.quantity, item.note) == ("雞腿便當", 120, 2, "不要辣")


def test_name_only():
    item = parse_item("大麥克套餐")
    assert (item.name, item.quantity, item.unit_price, item.note) == ("大麥克套餐", 1, None, "")


def test_multi_word_name_and_trailing_note():
    item = parse_item("Big Mac 85 半糖少冰")
    assert item.name == "Big Mac"
    assert item.unit_price == 85
    assert item.note == "半糖少冰"


def test_chinese_quantity_suffix_and_price_unit():
    item = parse_item("珍珠奶茶 55元 3杯")
    assert (item.unit_price, item.quantity) == (55, 3)


def test_first_token_never_price():
    item = parse_item("7 11 x1")
    assert item.name == "7"
    assert item.unit_price == 11


@pytest.mark.parametrize("text", ["", "   ", "#只有備註"])
def test_missing_name(text):
    with pytest.raises(ParseError):
        parse_item(text)


def test_quantity_bounds():
    with pytest.raises(ParseError):
        parse_item("便當 x0")
    with pytest.raises(ParseError):
        parse_item("便當 x100")
