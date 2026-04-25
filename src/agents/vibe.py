from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 분위기 평가 에이전트입니다.
데이트 코스의 흐름, 감성, 분위기가 요청과 맞는지 평가하세요.
반박이 있으면 반박하고 대안을 제시하세요.
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"score": 8, "feedback": "분위기 평가", "objection": null, "alternative": null}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"score": 7, "feedback": "", "objection": None, "alternative": None}
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    json_match = re.search(r"\{[\s\S]+\}", text)
    if json_match:
        text = json_match.group(0)
    return json.loads(text)


def evaluate_vibe(plan: dict, candidates: list, budget_result: dict) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"원하는 분위기: {plan['mood']}\n코스: {json.dumps(candidates, ensure_ascii=False)}\n예산 평가: {json.dumps(budget_result, ensure_ascii=False)}"},
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content or "{}"
    return _parse_json(content)
