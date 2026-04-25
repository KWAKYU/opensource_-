import os
import requests
import pandas as pd

BASE_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def search_places(keyword: str, x: str = None, y: str = None, radius: int = 2000) -> pd.DataFrame:
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_API_KEY')}"}
    params = {"query": keyword, "size": 10}
    if x and y:
        params.update({"x": x, "y": y, "radius": radius, "sort": "distance"})

    response = requests.get(BASE_URL, headers=headers, params=params)
    response.raise_for_status()

    documents = response.json().get("documents", [])
    if not documents:
        return pd.DataFrame()

    df = pd.DataFrame(documents)[["place_name", "category_name", "address_name", "distance", "place_url"]]
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0).astype(int)
    return df


def search_by_category(category: str, location: str, budget_per_place: int) -> pd.DataFrame:
    df = search_places(f"{location} {category}")
    df["estimated_cost"] = budget_per_place
    df["category"] = category
    return df
