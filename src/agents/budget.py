from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 예산 최적화 에이전트입니다.
제안된 데이트 코스가 총 예산 안에 맞는지 분석하고, 초과 시 대안을 제시하세요.
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"approved": true, "total_estimated": 숫자, "breakdown": [], "suggestion": "조정 의견"}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"approved": True, "total_estimated": 0, "breakdown": [], "suggestion": ""}
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    json_match = re.search(r"\{[\s\S]+\}", text)
    if json_match:
        text = json_match.group(0)
    return json.loads(text)


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
