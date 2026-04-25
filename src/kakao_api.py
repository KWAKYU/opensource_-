import os
import requests
import pandas as pd

BASE_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

# 소요 시간별 탐색 반경 (미터)
RADIUS_BY_DURATION = {
    "2시간":    600,
    "반나절":   900,
    "하루 종일": 1400,
}


def geocode_location(location: str) -> tuple:
    """지역명 → (경도 x, 위도 y) 반환. 역/상권 중심 우선, 실패 시 (None, None)"""
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_API_KEY')}"}
    # 지하철역 or 상권 중심으로 먼저 시도 (더 정확한 나들이 중심점)
    for query in [f"{location}역", f"{location} 번화가", location]:
        params = {"query": query, "size": 1}
        try:
            response = requests.get(BASE_URL, headers=headers, params=params, timeout=5)
            docs = response.json().get("documents", [])
            if docs:
                return docs[0]["x"], docs[0]["y"]
        except Exception:
            continue
    return None, None


def search_places(keyword: str, x=None, y=None, radius: int = 900) -> pd.DataFrame:
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_API_KEY')}"}
    params = {"query": keyword, "size": 15}
    if x and y:
        params.update({"x": x, "y": y, "radius": radius, "sort": "distance"})

    response = requests.get(BASE_URL, headers=headers, params=params)
    response.raise_for_status()

    documents = response.json().get("documents", [])
    if not documents:
        return pd.DataFrame()

    df = pd.DataFrame(documents)[["place_name", "category_name", "address_name", "distance", "place_url", "x", "y"]]
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0).astype(int)
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    return df


def search_by_category(category: str, location: str, budget_per_place: int,
                        duration: str = "반나절") -> pd.DataFrame:
    radius = RADIUS_BY_DURATION.get(duration, 900)

    # 지역 중심 좌표 조회
    cx, cy = geocode_location(location)

    if cx and cy:
        # 좌표 + 반경으로 정확한 범위 검색
        df = search_places(category, x=cx, y=cy, radius=radius)
    else:
        # 좌표 실패 시 키워드 검색 fallback
        df = search_places(f"{location} {category}")

    if df.empty:
        return df

    df["estimated_cost"] = budget_per_place
    df["category"] = category

    # 반경 초과 장소 명시적 필터 (distance > 0인 경우에만)
    if cx and cy and "distance" in df.columns:
        df = df[df["distance"] <= radius]

    return df
