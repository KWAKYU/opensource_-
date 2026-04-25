from openai import OpenAI
from src.kakao_api import search_by_category
from src.naver_api import add_blog_counts
import os, json, re
import pandas as pd

SYSTEM_PROMPT = """당신은 서울 나들이 코스의 장소 큐레이터(Scout)입니다.
주어진 후보 데이터에서 실제로 가볼 만한 곳만 엄선해서 JSON으로 반환하세요.

━━━ 선정 기준 최우선순위 ━━━

【인기도 > 거리 > 가격】 — 가까운 곳보다 유명한 곳이 우선이다

[blog_count 필드 활용 — 핵심 지표]
- blog_count: 네이버 블로그 언급 수 → 높을수록 실제 방문자가 많은 인기 장소
- blog_count 1000 이상: 검증된 인기 장소 → 강력 우선 선택
- blog_count 300~999: 준인기 장소 → 테마 맞으면 선택
- blog_count 100 미만: 신생·무명 장소 → 다른 후보가 있으면 제외
- blog_count 0: 온라인 존재감 없음 → 원칙적으로 제외

[절대 제외 — 품질 필터]
- 지하철역 내부·지하상가 음식점 (address에 "지하" 포함)
- 이름이 "○○역 ○○", "역사 내 ○○" 형태인 곳
- 분식집, 저가 간식 포장마차 (3,000~5,000원대 저가 식사)
- 무명 체인, 프랜차이즈 느낌의 일반 가게
- 온라인 존재감이 거의 없는 신생·무명 장소

[우선 선택 조건]
- 해당 지역 대표 핫플레이스, SNS·블로그 자주 언급되는 곳
- 인스타그램 태그가 많을 것 같은 감성 장소
- 현지인이 아닌 외부 방문자(서울 나들이객)도 찾아오는 목적지형 장소
- 평균 이상 가격대 (맛집 1인 15,000원 이상, 카페 7,000원 이상)

[카테고리 분류 기준 — 반드시 아래 중 하나만 사용]
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

[절대 제외]
- 스터디카페, 독서실, 병원, 약국, 은행, 편의점
- 체인점 제외 요청 시: 체인카페·패스트푸드 카테고리 모두 제외

[추천 이유 — 반드시 구체적으로]
- reason 필드에 "이 장소가 이 코스에 왜 좋은지" 구체적으로 작성
- "좋은 카페입니다" 같은 모호한 이유 금지
- 예: "성수동 감성 인더스트리얼 카페로 인스타 핫플, 루프탑 뷰가 테마에 딱 맞음"

반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"candidates": [{"name": "장소명", "category": "카테고리", "address": "주소", "reason": "구체적 추천 이유"}]}"""


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


def scout(plan: dict, exclude_places: list = None, previous_feedback: str = None) -> list:
    """
    exclude_places: 이미 추천된 장소명 목록 (리롤 시 제외)
    previous_feedback: 이전 라운드 Experience 에이전트의 반박/피드백 (재토론 시 반영)
    """
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    location = plan["location"]
    budget_per = plan["budget_total"] // max(len(plan["schedule"]), 1)
    exclude_set = set(exclude_places or [])

    candidates = []
    coord_map = {}
    duration = plan.get("duration", "반나절")
    for item in plan["schedule"]:
        df = search_by_category(item, location, budget_per, duration=duration)
        if not df.empty:
            # 제외 장소 필터링 후 최대 8개
            df_filtered = df[~df["place_name"].isin(exclude_set)]
            top = df_filtered.head(8) if not df_filtered.empty else df.head(8)
            candidates.append(top.to_dict(orient="records"))
            for _, row in top.iterrows():
                coord_map[row["place_name"]] = {
                    "lat": float(row["y"]) if pd.notna(row["y"]) else None,
                    "lng": float(row["x"]) if pd.notna(row["x"]) else None,
                }

    # 네이버 블로그 언급수로 인기도 지표 추가
    print("    [블로그 카운트] 후보 장소 인기도 조회 중...")
    candidates = add_blog_counts(candidates)

    exclude_note = f"\n제외할 장소 (이미 추천됨, 절대 포함 금지): {list(exclude_set)}" if exclude_set else ""
    feedback_note = f"\n\n★ 이전 라운드 평가에서 지적된 문제점 — 반드시 반영하여 개선된 장소 선택:\n{previous_feedback}" if previous_feedback else ""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"플랜: {json.dumps(plan, ensure_ascii=False)}\n후보 데이터 (blog_count=네이버 블로그 언급수·인기도): {json.dumps(candidates, ensure_ascii=False)}{exclude_note}{feedback_note}"},
        ],
        max_tokens=1200,
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

    duration = plan.get("duration", "반나절")
    df = search_by_category(category, location, budget_per, duration=duration)
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

    enriched = add_blog_counts([candidates])
    candidates = enriched[0] if enriched else candidates

    exclude_note = f"\n제외할 장소: {list(exclude_set)}" if exclude_set else ""
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"아래 후보 중 {category} 카테고리에서 가장 적합한 장소 1곳만 추천하세요 (blog_count 높은 곳 우선).\n후보: {json.dumps(candidates, ensure_ascii=False)}{exclude_note}"},
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
