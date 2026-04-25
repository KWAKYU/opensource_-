from openai import OpenAI
from src.kakao_api import search_by_category
import os, json, re

SYSTEM_PROMPT = """당신은 장소 탐색 에이전트입니다.
주어진 장소 데이터를 분석해서 코스에 적합한 후보를 추려 JSON으로 반환하세요.

[카테고리 분류 규칙 - 반드시 정확히 분류]
- 카페: 음료·디저트 전문점 (일반 카페, 베이커리 카페)
- 방탈출: 방탈출 카페, 미션게임 — 절대 카페로 분류하지 말 것
- 맛집: 식사 가능한 음식점
- 액티비티: 방탈출, 볼링, 노래방, 클라이밍 등 체험 활동
- 문화: 전시회, 미술관, 박물관

[체인점 처리 규칙]
- 사용자 입력에 "체인점 제외"가 있으면: 스타벅스, 메가커피, 이디야, 컴포즈, 투썸플레이스, 맥도날드, 버거킹, KFC, 롯데리아, 파리바게뜨, 뚜레쥬르 등 프랜차이즈 브랜드 완전 제외
- "체인점 포함"이거나 언급 없으면: 모든 장소 포함 가능

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


def scout(plan: dict) -> list:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    location = plan["location"]
    budget_per = plan["budget_total"] // max(len(plan["schedule"]), 1)

    candidates = []
    for item in plan["schedule"]:
        df = search_by_category(item, location, budget_per)
        if not df.empty:
            candidates.append(df.head(3).to_dict(orient="records"))

    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"플랜: {json.dumps(plan, ensure_ascii=False)}\n후보 데이터: {json.dumps(candidates, ensure_ascii=False)}"},
        ],
        max_tokens=800,
    )
    content = response.choices[0].message.content or "{}"
    result = _parse_json(content)
    return result.get("candidates", []) if isinstance(result, dict) else result
