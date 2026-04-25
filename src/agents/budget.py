from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 예산 최적화 에이전트입니다.
제안된 데이트 코스가 총 예산 안에 맞는지 분석하고, 초과 시 대안을 제시하세요.
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"approved": true, "total_estimated": 숫자, "breakdown": [], "suggestion": "조정 의견"}"""


def _parse_json(text: str, fallback: dict = None) -> dict:
    text = text.strip()
    if not text:
        return fallback or {"approved": True, "total_estimated": 0, "breakdown": [], "suggestion": ""}
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
        return fallback or {"approved": True, "total_estimated": 0, "breakdown": [], "suggestion": ""}


def evaluate_budget(plan: dict, candidates: list) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"총 예산: {plan['budget_total']}원\n인원: {plan['people']}명\n후보 코스: {json.dumps(candidates, ensure_ascii=False)}"},
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content or "{}"
    return _parse_json(content)
