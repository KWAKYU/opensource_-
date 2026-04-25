from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 서울 나들이 코스의 크리에이티브 디렉터입니다.
사용자의 요청을 받아 자연스럽고 다채로운 하루 코스를 설계하세요.

[코스 설계 원칙 — 반드시 지킬 것]
1. 같은 카테고리를 연속으로 배치하지 말 것 (맛집→맛집 ❌, 카페→카페 ❌)

2. ★ 핵심 규칙: 카페·디저트·체인카페는 모두 "음료/단것" 계열로 간주
   - 카페 다음에 디저트 ❌  /  디저트 다음에 카페 ❌
   - 카페→디저트→카페 같은 패턴은 절대 금지
   - 카페 계열은 전체 코스에서 최대 2곳까지만 허용
   - 카페 계열 2곳 사이에는 반드시 다른 계열(맛집/액티비티/문화·전시 등)이 1개 이상 있어야 함

3. 사람의 하루 흐름처럼 자연스럽게 구성할 것
   - 좋은 예: 맛집 → 카페 → 포토스팟 → 디저트 (사이에 활동 있음)
   - 나쁜 예: 카페 → 디저트 → 카페 (음료/단것 3연속 ❌)

4. 테마에 맞게 카테고리를 조합할 것
   - 맛집투어: 맛집 → 카페 → 맛집2 (카페 계열은 한 번만)
   - 카페투어: 카페 → 포토스팟 → 카페2 (중간에 포토스팟/산책 등 삽입)
   - 문화/예술: 전시 → 카페 → 공방·체험
   - 힐링: 공원·자연 → 카페 → 맛집
   - 액티비티: 액티비티 → 맛집 → 카페

5. 소요 시간에 맞게 장소 수 조정
   - 2시간: 2곳, 반나절: 3곳, 하루 종일: 4~5곳

6. schedule 배열의 각 항목은 Scout가 검색할 카테고리명 (카페/맛집/디저트/방탈출/공방·체험/액티비티/문화·전시/포토스팟/쇼핑/공원·자연 중 하나)

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


# 카페 계열로 묶이는 카테고리 (연속 배치 금지)
CAFE_GROUP = {"카페", "디저트", "체인카페"}

def _fix_schedule(schedule: list) -> list:
    """카페 계열 연속 배치 자동 수정 — 두 번째 항목을 제거"""
    if len(schedule) < 2:
        return schedule
    fixed = [schedule[0]]
    for cat in schedule[1:]:
        if cat in CAFE_GROUP and fixed[-1] in CAFE_GROUP:
            continue  # 카페 계열 연속 → 제거
        fixed.append(cat)
    return fixed


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
    result = _parse_json(content)
    result["schedule"] = _fix_schedule(result.get("schedule", []))
    return result
