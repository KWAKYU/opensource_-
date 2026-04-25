import os
import requests
import pandas as pd
from src.seoul_spots import get_spot_info
from src.naver_api import search_places_naver

BASE_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

# 소요 시간별 기본 탐색 반경 (미터) — seoul_spots에 반경 있으면 그걸 우선 사용
RADIUS_BY_DURATION = {
    "2시간":    600,
    "반나절":   900,
    "하루 종일": 1400,
}


def geocode_location(location: str) -> tuple:
    """
    1순위: seoul_spots 사전 (해방촌·연남동 등 정확한 상권 중심)
    2순위: Kakao 지하철역 검색
    3순위: Kakao 키워드 검색
    반환: (x경도, y위도) 또는 (None, None)
    """
    # 1. 직접 정의된 서울 상권 사전
    spot = get_spot_info(location)
    if spot:
        return spot[0], spot[1]

    # 2. Kakao — 역 우선
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_API_KEY')}"}
    for query in [f"{location}역", location]:
        params = {"query": query, "size": 1}
        try:
            response = requests.get(BASE_URL, headers=headers, params=params, timeout=5)
            docs = response.json().get("documents", [])
            if docs:
                return docs[0]["x"], docs[0]["y"]
        except Exception:
            continue
    return None, None


def get_radius(location: str, duration: str) -> int:
    """상권별 고정 반경 우선, 없으면 duration 기반 기본값"""
    spot = get_spot_info(location)
    if spot:
        return spot[2]  # seoul_spots의 반경
    return RADIUS_BY_DURATION.get(duration, 900)


SUBWAY_KEYWORDS = ["지하", "지하상가", "지하도", "역사", "지하철"]


def search_places(keyword: str, x=None, y=None, radius: int = 900) -> pd.DataFrame:
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_API_KEY')}"}
    params = {"query": keyword, "size": 20}
    if x and y:
        # Kakao는 좌표 검색 시 sort=accuracy 미지원 → distance 사용
        params.update({"x": x, "y": y, "radius": radius, "sort": "distance"})
    else:
        params["sort"] = "accuracy"

    response = requests.get(BASE_URL, headers=headers, params=params)
    response.raise_for_status()

    documents = response.json().get("documents", [])
    if not documents:
        return pd.DataFrame()

    df = pd.DataFrame(documents)[["place_name", "category_name", "address_name", "distance", "place_url", "x", "y"]]
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0).astype(int)
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")

    # 지하철역 내부·지하상가 장소 제외 (분식집·패스트푸드 등 역사 내 저품질 가게)
    mask = df["address_name"].apply(
        lambda addr: not any(k in str(addr) for k in SUBWAY_KEYWORDS)
    )
    df = df[mask]

    return df


def search_by_category(category: str, location: str, budget_per_place: int,
                        duration: str = "반나절") -> pd.DataFrame:
    radius = get_radius(location, duration)

    # 지역 중심 좌표 조회
    cx, cy = geocode_location(location)

    if cx and cy:
        # 좌표 + 반경으로 정확한 범위 검색
        df = search_places(category, x=cx, y=cy, radius=radius)
    else:
        # 좌표 실패 시 키워드 검색 fallback
        df = search_places(f"{location} {category}")

    # Kakao 결과 없으면 Naver 지역 검색 fallback
    if df.empty:
        df = search_places_naver(category, location)

    if df.empty:
        return df

    df["estimated_cost"] = budget_per_place
    df["category"] = category

    # 반경 초과 장소 명시적 필터 (distance > 0인 경우에만, Kakao 결과만)
    if cx and cy and "distance" in df.columns:
        df = df[(df["distance"] == 0) | (df["distance"] <= radius)]

    return df
