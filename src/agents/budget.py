from openai import OpenAI
import os, json

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """당신은 예산 최적화 에이전트입니다.
제안된 데이트 코스가 총 예산 안에 맞는지 분석하고,
초과 시 대안을 제시하거나 조합을 수정하세요.
JSON으로 응답: {"approved": true/false, "total_estimated": 숫자, "breakdown": [...], "suggestion": "조정 의견"}"""


def evaluate_budget(plan: dict, candidates: list) -> dict:
    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"총 예산: {plan['budget_total']}원\n인원: {plan['people']}명\n후보 코스: {json.dumps(candidates, ensure_ascii=False)}"},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
