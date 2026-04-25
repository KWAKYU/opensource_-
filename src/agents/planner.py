from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 서울 코스 추천 팀의 오케스트레이터입니다.
사용자 요청을 분석해서 Scout, Budget, Experience 에이전트에게 명확한 지시를 내리세요.
반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "location": "지역명",
  "budget_total": 예산(숫자만),
  "people": 인원수(숫자만),
  "theme": "코스 테마 키워드",
  "schedule": ["맛집", "카페", "볼거리"],
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
        model="anthropic/claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content or ""
    return _parse_json(content)
