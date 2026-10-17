import pytest

from bot.platforms import PLATFORMS, is_platform_url, resolve_platform
from bot.storage import Storage, StorageError
from bot.summary import build_summary


@pytest.fixture
def store():
    s = Storage()
    yield s
    s.close()


def open_session(store, chat_id=1):
    return store.open_session(chat_id, "foodpanda", "八方雲集", None, 10, "Amy")


def test_one_open_session_per_chat(store):
    open_session(store)
    with pytest.raises(StorageError):
        open_session(store)
    open_session(store, chat_id=2)  # 其他群組不受影響


def test_close_then_new_session(store):
    s = open_session(store)
    store.set_status(s.id, "closed")
    assert store.current_session(1) is None
    s2 = open_session(store)
    assert store.last_session(1).id == s2.id
    with pytest.raises(StorageError):
        store.reopen(s.id)


def test_remove_only_own_item(store):
    s = open_session(store)
    item = store.add_item(s.id, 20, "Bob", "鍋貼", 10, 6, "")
    assert not store.remove_item(s.id, item.id, user_id=30)
    assert store.remove_item(s.id, item.id, user_id=20)
    assert store.items(s.id) == []


def test_organizer_removes_any_item(store):
    s = open_session(store)
    item = store.add_item(s.id, 20, "Bob", "鍋貼", 10, 6, "")
    assert store.remove_item(s.id, item.id, user_id=None)


def test_summary_groups_items_and_totals(store):
    s = open_session(store)
    store.add_item(s.id, 20, "Bob", "鍋貼", 10, 6, "")
    store.add_item(s.id, 30, "Cat", "鍋貼", 5, 6, "")
    store.add_item(s.id, 30, "Cat", "酸辣湯", 1, None, "")
    text = build_summary(store.get_session(s.id), store.items(s.id))
    assert "鍋貼 ×15" in text
    assert "共 2 人、16 份" in text
    assert "餐點小計 $90" in text
    assert "部分品項未填價格" in text


def test_summary_escapes_html(store):
    s = open_session(store)
    store.add_item(s.id, 20, "<b>Bob</b>", "<script>", 1, None, "")
    text = build_summary(store.get_session(s.id), store.items(s.id))
    assert "<script>" not in text
    assert "&lt;b&gt;Bob&lt;/b&gt;" in text


def test_platform_aliases_and_urls():
    assert resolve_platform("FP").key == "foodpanda"
    assert resolve_platform("Uber Eats").key == "ubereats"
    assert resolve_platform("lalamove") is None
    fp = PLATFORMS["foodpanda"]
    assert is_platform_url(fp, "https://www.foodpanda.com.tw/restaurant/abc")
    assert not is_platform_url(fp, "https://foodpanda.com.tw.evil.com/")
    assert not is_platform_url(fp, "javascript:alert(1)")
    ue = PLATFORMS["ubereats"]
    assert ue.link_for("麥當勞", None) == "https://www.ubereats.com/tw/search?q=%E9%BA%A5%E7%95%B6%E5%8B%9E"
