from openai import OpenAI
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """당신은 데이트 플래닝 팀의 오케스트레이터입니다.
사용자 요청을 분석해서 Scout, Budget, Vibe 에이전트에게 명확한 지시를 내리세요.
JSON 형식으로 응답하세요:
{
  "location": "지역명",
  "budget_total": 예산(숫자),
  "people": 인원수,
  "mood": "분위기 키워드",
  "schedule": ["저녁식사", "카페", "산책 등"],
  "constraints": ["이동거리 최소화 등 제약사항"]
}"""


def plan(user_input: str) -> dict:
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content)
