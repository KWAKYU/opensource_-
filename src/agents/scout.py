from openai import OpenAI
from src.kakao_api import search_by_category
import os, json, re
import pandas as pd

SYSTEM_PROMPT = """당신은 장소 탐색 에이전트입니다.
주어진 장소 데이터를 분석해서 코스에 적합한 후보를 추려 JSON으로 반환하세요.

━━━ 카테고리 분류 기준 (반드시 아래 중 하나만 사용) ━━━

| category 값  | 해당하는 장소 | 절대 포함하지 말 것 |
|-------------|-------------|-----------------|
| 카페         | 음료·디저트 전문 독립 카페, 베이커리 카페, 북카페, 애견 카페 | 방탈출카페, 공방카페, 스터디카페, 체인 카페 |
| 체인카페      | 스타벅스, 메가커피, 이디야, 컴포즈, 투썸플레이스, 할리스, 빽다방 등 프랜차이즈 카페 | |
| 맛집         | 식사 가능한 음식점 (한식·일식·양식·중식 등) | 카페, 디저트 전문점 |
| 패스트푸드    | 맥도날드, 버거킹, KFC, 롯데리아, 서브웨이 등 패스트푸드 체인 | |
| 디저트       | 케이크샵, 마카롱 전문점, 빙수 전문점, 아이스크림 가게 (독립 매장) | |
| 방탈출       | 방탈출 카페, 미션게임방 — 이름에 '카페' 있어도 반드시 방탈출로 분류 | |
| 공방·체험    | 도자기 공방, 가죽 공방, 캔들 공방, 플라워 클래스 등 만들기 체험 | |
| 액티비티     | 볼링, 노래방, 클라이밍, 서핑, VR, 양궁, 당구 등 신체 활동 | 방탈출(별도 분류) |
| 문화·전시    | 미술관, 박물관, 갤러리, 전시회, 팝업스토어 | |
| 포토스팟     | 포토부스, 사진관, 루프탑, 인생네컷, 포토스튜디오 | |
| 쇼핑         | 쇼핑몰, 편집샵, 빈티지샵, 시장 | |
| 바·주점      | 이자카야, 와인바, 칵테일바, 루프탑바, 맥주집 | |
| 공원·자연    | 한강공원, 서울숲, 올림픽공원 등 야외 공간 | |

[제외 대상 - 코스에 부적합]
- 스터디카페, 독서실 (여가 목적 아님)
- 병원, 약국, 은행
- 편의점 단독 추천

[체인점 처리]
- 사용자 입력에 "체인점 제외"가 있으면: category가 체인카페·패스트푸드인 장소 모두 제외
- "체인점 포함"이면: 모든 카테고리 포함 가능

반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"candidates": [{"name": "장소명", "category": "카테고리", "address": "주소", "reason": "추천 이유"}]}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"candidates": []}
    # ```json 블록 추출
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    # 첫 { 부터 매칭되는 마지막 } 까지만 추출
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    text = text[start:i+1]
                    break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"candidates": []}


def scout(plan: dict, exclude_places: list = None) -> list:
    """
    exclude_places: 이미 추천된 장소명 목록 (리롤 시 제외)
    """
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    location = plan["location"]
    budget_per = plan["budget_total"] // max(len(plan["schedule"]), 1)
    exclude_set = set(exclude_places or [])

    candidates = []
    coord_map = {}
    for item in plan["schedule"]:
        df = search_by_category(item, location, budget_per)
        if not df.empty:
            # 제외 장소 필터링 후 최대 6개
            df_filtered = df[~df["place_name"].isin(exclude_set)]
            top = df_filtered.head(6) if not df_filtered.empty else df.head(6)
            candidates.append(top.to_dict(orient="records"))
            for _, row in top.iterrows():
                coord_map[row["place_name"]] = {
                    "lat": float(row["y"]) if pd.notna(row["y"]) else None,
                    "lng": float(row["x"]) if pd.notna(row["x"]) else None,
                }

    exclude_note = f"\n제외할 장소 (이미 추천됨, 절대 포함 금지): {list(exclude_set)}" if exclude_set else ""
    response = client.chat.completions.create(
        model="google/gemma-3-27b-it",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"플랜: {json.dumps(plan, ensure_ascii=False)}\n후보 데이터: {json.dumps(candidates, ensure_ascii=False)}{exclude_note}"},
        ],
        max_tokens=1000,
    )
    content = response.choices[0].message.content or "{}"
    result = _parse_json(content)
    places = result.get("candidates", []) if isinstance(result, dict) else result

    for p in places:
        name = p.get("name", "")
        coords = coord_map.get(name, {})
        p["lat"] = coords.get("lat")
        p["lng"] = coords.get("lng")

    return places


def scout_one(plan: dict, category: str, exclude_places: list = None) -> dict:
    """단일 장소 리롤 — 특정 카테고리에서 새 장소 1개 반환"""
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    location = plan["location"]
    budget_per = plan["budget_total"] // max(len(plan.get("schedule", [1])), 1)
    exclude_set = set(exclude_places or [])

    df = search_by_category(category, location, budget_per)
    coord_map = {}
    if not df.empty:
        df_filtered = df[~df["place_name"].isin(exclude_set)]
        top = df_filtered.head(6) if not df_filtered.empty else df.head(6)
        candidates = top.to_dict(orient="records")
        for _, row in top.iterrows():
            coord_map[row["place_name"]] = {
                "lat": float(row["y"]) if pd.notna(row["y"]) else None,
                "lng": float(row["x"]) if pd.notna(row["x"]) else None,
            }
    else:
        return {}

    exclude_note = f"\n제외할 장소: {list(exclude_set)}" if exclude_set else ""
    response = client.chat.completions.create(
        model="google/gemma-3-27b-it",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"아래 후보 중 {category} 카테고리에서 가장 적합한 장소 1곳만 추천하세요.\n후보: {json.dumps(candidates, ensure_ascii=False)}{exclude_note}"},
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content or "{}"
    result = _parse_json(content)
    places = result.get("candidates", []) if isinstance(result, dict) else result
    if places:
        p = places[0]
        coords = coord_map.get(p.get("name", ""), {})
        p["lat"] = coords.get("lat")
        p["lng"] = coords.get("lng")
        return p
    return {}
