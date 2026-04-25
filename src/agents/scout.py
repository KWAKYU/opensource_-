from openai import OpenAI
from src.kakao_api import search_by_category
import os, json

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """당신은 장소 탐색 에이전트입니다.
주어진 장소 데이터를 분석해서 데이트 코스에 적합한 후보를 추려 JSON 배열로 반환하세요.
각 항목: {"name": "장소명", "category": "카테고리", "address": "주소", "reason": "추천 이유"}"""


def scout(plan: dict) -> list:
    location = plan["location"]
    budget_per = plan["budget_total"] // max(len(plan["schedule"]), 1)

    candidates = []
    for item in plan["schedule"]:
        df = search_by_category(item, location, budget_per)
        if not df.empty:
            candidates.append(df.head(3).to_dict(orient="records"))

    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"플랜: {json.dumps(plan, ensure_ascii=False)}\n후보 데이터: {json.dumps(candidates, ensure_ascii=False)}"},
        ],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    return result.get("candidates", result) if isinstance(result, dict) else result
