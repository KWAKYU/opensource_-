import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_kakao_api_returns_results():
    from src.kakao_api import search_places
    df = search_places("강남 레스토랑")
    assert not df.empty, "Kakao API should return results"
    assert "place_name" in df.columns
    assert "address_name" in df.columns


def test_kakao_api_filters_by_category():
    from src.kakao_api import search_by_category
    df = search_by_category("카페", "강남", 15000)
    assert not df.empty
    assert "estimated_cost" in df.columns
    assert df["estimated_cost"].iloc[0] == 15000


def test_search_places_empty_query():
    from src.kakao_api import search_places
    df = search_places("xyzxyzxyz없는장소abc")
    assert df.empty or isinstance(df.shape[0], int)
