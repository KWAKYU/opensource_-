from openai import OpenAI
import os, json

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """당신은 분위기 평가 에이전트입니다.
데이트 코스의 전체적인 흐름, 감성, 분위기가 요청과 맞는지 평가하세요.
너무 단조롭거나 분위기가 안 맞으면 반박하고 대안을 제시하세요.
JSON으로 응답: {"score": 1-10, "feedback": "분위기 평가", "objection": "반박 내용(없으면 null)", "alternative": "대안(없으면 null)"}"""


def evaluate_vibe(plan: dict, candidates: list, budget_result: dict) -> dict:
    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"원하는 분위기: {plan['mood']}\n코스: {json.dumps(candidates, ensure_ascii=False)}\n예산 평가: {json.dumps(budget_result, ensure_ascii=False)}"},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
