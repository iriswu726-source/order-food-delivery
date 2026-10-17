"""外送平台定義：名稱、別名與預設連結。

foodpanda 與 Uber Eats 都沒有開放「以消費者身分下單」的公開 API，
因此 bot 不會替使用者送出訂單，而是彙整團購內容並提供平台連結
（建議使用平台內建的「團體訂單 / Group Order」分享連結），
由團主在平台上一次下單、付款。
"""

from dataclasses import dataclass
from urllib.parse import quote, urlparse


@dataclass(frozen=True)
class Platform:
    key: str
    name: str
    home_url: str
    domains: tuple[str, ...]
    search_url: str | None = None

    def link_for(self, restaurant: str, url: str | None) -> str:
        if url:
            return url
        if self.search_url:
            return self.search_url.format(q=quote(restaurant))
        return self.home_url


PLATFORMS: dict[str, Platform] = {
    "foodpanda": Platform(
        key="foodpanda",
        name="foodpanda",
        home_url="https://www.foodpanda.com.tw/",
        domains=("foodpanda.com.tw", "foodpanda.com", "fd.link"),
    ),
    "ubereats": Platform(
        key="ubereats",
        name="Uber Eats",
        home_url="https://www.ubereats.com/tw",
        domains=("ubereats.com", "uber.com", "eats.uber.com"),
        search_url="https://www.ubereats.com/tw/search?q={q}",
    ),
}

ALIASES = {
    "foodpanda": "foodpanda",
    "fp": "foodpanda",
    "panda": "foodpanda",
    "熊貓": "foodpanda",
    "ubereats": "ubereats",
    "uber": "ubereats",
    "ue": "ubereats",
    "ubereat": "ubereats",
}


def resolve_platform(text: str) -> Platform | None:
    key = ALIASES.get(text.strip().lower().replace(" ", ""))
    return PLATFORMS.get(key) if key else None


def is_platform_url(platform: Platform, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(host == d or host.endswith("." + d) for d in platform.domains)
