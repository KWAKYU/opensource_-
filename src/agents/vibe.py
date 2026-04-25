from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 코스 경험 평가 에이전트입니다.
추천된 코스의 흐름, 동선, 테마 일치도를 평가하세요.
코스가 단조롭거나 테마와 맞지 않으면 반박하고 개선안을 제시하세요.
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"score": 8, "feedback": "코스 평가", "objection": null, "alternative": null}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"score": 7, "feedback": "", "objection": None, "alternative": None}
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
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
        return {"score": 7, "feedback": "", "objection": None, "alternative": None}


def evaluate_vibe(plan: dict, candidates: list, budget_result: dict) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"코스 테마: {plan.get('theme', plan.get('mood', ''))}\n코스: {json.dumps(candidates, ensure_ascii=False)}\n예산 평가: {json.dumps(budget_result, ensure_ascii=False)}"},
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content or "{}"
    return _parse_json(content)
