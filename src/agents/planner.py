from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 데이트 플래닝 팀의 오케스트레이터입니다.
사용자 요청을 분석해서 Scout, Budget, Vibe 에이전트에게 명확한 지시를 내리세요.
반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "location": "지역명",
  "budget_total": 예산(숫자만),
  "people": 인원수(숫자만),
  "mood": "분위기 키워드",
  "schedule": ["저녁식사", "카페"],
  "constraints": ["이동거리 최소화"]
}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    # ```json ... ``` 블록 제거
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def plan(user_input: str) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )
    content = response.choices[0].message.content or ""
    return _parse_json(content)
