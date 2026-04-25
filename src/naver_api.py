import os
import requests
import re
import pandas as pd

BLOG_SEARCH_URL = "https://openapi.naver.com/v1/search/blog.json"
LOCAL_SEARCH_URL = "https://openapi.naver.com/v1/search/local.json"


def _naver_headers() -> dict:
    return {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID", ""),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET", ""),
    }


def search_places_naver(keyword: str, location: str) -> pd.DataFrame:
    """네이버 지역 검색 API — Kakao 결과 없을 때 fallback"""
    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"]:
        return pd.DataFrame()

    params = {"query": f"{location} {keyword}", "display": 5, "sort": "comment"}
    try:
        response = requests.get(LOCAL_SEARCH_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return pd.DataFrame()

    if not items:
        return pd.DataFrame()

    rows = []
    for item in items:
        # HTML 태그 제거
        name = re.sub(r"<[^>]+>", "", item.get("title", ""))
        # mapx/mapy → 실제 경위도 (1/10,000,000 단위)
        try:
            x = int(item.get("mapx", 0)) / 10_000_000
            y = int(item.get("mapy", 0)) / 10_000_000
        except Exception:
            x, y = None, None
        rows.append({
            "place_name": name,
            "category_name": item.get("category", ""),
            "address_name": item.get("address", ""),
            "distance": 0,
            "place_url": item.get("link", ""),
            "x": x,
            "y": y,
        })

    return pd.DataFrame(rows)


def search_price_from_blog(place_name: str) -> str:
    """네이버 블로그에서 장소 가격 정보 검색"""
    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"]:
        return ""
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


def search_vibe_from_blog(place_name: str) -> str:
    """네이버 블로그에서 장소 분위기/후기 정보 검색"""
    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"]:
        return ""
    params = {"query": f"{place_name} 분위기 후기", "display": 3, "sort": "sim"}

    try:
        response = requests.get(BLOG_SEARCH_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return ""

    # HTML 태그 제거 후 분위기 관련 키워드 추출
    vibe_keywords = ["분위기", "조용", "시끄럽", "넓", "좁", "아늑", "인스타", "감성", "뷰", "야경",
                     "데이트", "친구", "혼자", "커플", "북적", "힐링", "모던", "빈티지", "아기자기"]
    vibe_info = []
    for item in items:
        description = re.sub(r"<[^>]+>", "", item.get("description", ""))
        title = re.sub(r"<[^>]+>", "", item.get("title", ""))
        # 분위기 키워드 포함된 문장만 추출
        sentences = re.split(r"[.!?。]", description)
        relevant = [s.strip() for s in sentences
                    if any(k in s for k in vibe_keywords) and len(s.strip()) > 5]
        if relevant:
            vibe_info.append(f"{title}: {' / '.join(relevant[:2])}")

    return "\n".join(vibe_info) if vibe_info else ""


def get_blog_count(place_name: str) -> int:
    """네이버 블로그 언급 수 조회 — 인기도 지표로 사용"""
    headers = _naver_headers()
    if not headers["X-Naver-Client-Id"]:
        return 0
    params = {"query": place_name, "display": 1, "sort": "sim"}
    try:
        r = requests.get(BLOG_SEARCH_URL, headers=headers, params=params, timeout=2)
        r.raise_for_status()
        return r.json().get("total", 0)
    except Exception:
        return 0


def add_blog_counts(candidates_per_category: list) -> list:
    """후보 리스트에 blog_count 필드 추가 (Scout용)"""
    enriched = []
    for group in candidates_per_category:
        enriched_group = []
        for place in group:
            count = get_blog_count(place.get("place_name", ""))
            enriched_group.append({**place, "blog_count": count})
        enriched.append(enriched_group)
    return enriched


def get_vibes_for_candidates(candidates: list) -> dict:
    """후보 장소 목록의 분위기 정보를 일괄 수집"""
    vibe_data = {}
    for c in candidates:
        name = c.get("name", "")
        if name:
            info = search_vibe_from_blog(name)
            if info:
                vibe_data[name] = info
    return vibe_data
