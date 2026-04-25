from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 서울 나들이 코스의 크리에이티브 디렉터입니다.
사용자의 요청을 받아 자연스럽고 다채로운 하루 코스를 설계하세요.

[코스 설계 원칙 — 반드시 지킬 것]
1. 같은 카테고리를 연속으로 배치하지 말 것 (맛집→맛집 ❌, 카페→카페 ❌)
2. 사람의 하루 흐름처럼 자연스럽게 구성할 것
   - 식사 → 디저트/카페 → 산책/볼거리 → 활동 (예시일 뿐, 창의적으로 변형 가능)
3. 테마에 맞게 카테고리를 조합할 것
   - 맛집투어: 맛집 → 카페/디저트 → 맛집2 (사이에 다른 활동 끼우기)
   - 카페투어: 카페 → 포토스팟 → 카페2 → 디저트
   - 문화/예술: 전시 → 카페 → 공방·체험
   - 힐링: 공원·자연 → 카페 → 디저트
   - 액티비티: 액티비티 → 맛집 → 카페
4. 소요 시간에 맞게 장소 수 조정
   - 2시간: 2곳, 반나절: 3곳, 하루 종일: 4~5곳
5. schedule 배열의 각 항목은 Scout가 검색할 카테고리명 (카페/맛집/디저트/방탈출/공방·체험/액티비티/문화·전시/포토스팟/쇼핑/공원·자연 중 하나)

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "location": "지역명",
  "budget_total": 예산(숫자만),
  "people": 인원수(숫자만),
  "theme": "코스 테마 키워드",
  "duration": "2시간 또는 반나절 또는 하루 종일",
  "schedule": ["맛집", "카페", "포토스팟"],
  "constraints": ["이동거리 최소화 등 제약사항"]
}"""


def _parse_json(text: str) -> dict:
    fallback = {
        "location": "서울",
        "budget_total": 50000,
        "people": 2,
        "theme": "나들이",
        "schedule": ["맛집", "카페"],
        "constraints": []
    }
    if not text or not text.strip():
        return fallback
    text = text.strip()
    # ```json 블록 추출
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    # bracket-depth로 정확한 JSON 범위 추출
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    text = text[start:i+1]
                    break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback


def plan(user_input: str) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.6",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content or ""
    return _parse_json(content)
