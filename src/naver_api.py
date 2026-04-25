import os
import requests
import re


NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"


def search_price_from_blog(place_name: str) -> str:
    """네이버 블로그에서 장소 가격 정보 검색"""
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        return ""

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": f"{place_name} 가격", "display": 5, "sort": "sim"}

    try:
        response = requests.get(BLOG_SEARCH_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return ""

    # HTML 태그 제거 후 가격 관련 텍스트 추출
    price_info = []
    price_pattern = re.compile(r"[\d,]+\s*원")

    for item in items:
        description = re.sub(r"<[^>]+>", "", item.get("description", ""))
        prices = price_pattern.findall(description)
        if prices:
            price_info.append(f"{item.get('title', '')} - 언급 가격: {', '.join(prices[:3])}")

    return "\n".join(price_info) if price_info else ""


def get_prices_for_candidates(candidates: list) -> dict:
    """후보 장소 목록의 가격 정보를 일괄 수집"""
    price_data = {}
    for c in candidates:
        name = c.get("name", "")
        if name:
            info = search_price_from_blog(name)
            if info:
                price_data[name] = info
    return price_data
