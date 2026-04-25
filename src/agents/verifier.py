from openai import OpenAI
import os, json

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = """당신은 최종 검증 에이전트(Claude)입니다.
Scout, Budget, Vibe 에이전트의 토론 결과를 종합해서 최적의 데이트 코스를 확정하세요.
모든 에이전트의 의견을 고려하되, 최종 판단은 당신이 합니다.
JSON으로 응답:
{
  "final_course": [{"order": 1, "place": "장소명", "category": "카테고리", "address": "주소", "estimated_cost": 숫자}],
  "total_cost": 숫자,
  "verdict": "최종 판단 근거",
  "debate_summary": "토론 요약"
}"""


def verify(plan: dict, candidates: list, budget_result: dict, vibe_result: dict) -> dict:
    debate_context = {
        "original_plan": plan,
        "scout_candidates": candidates,
        "budget_evaluation": budget_result,
        "vibe_evaluation": vibe_result,
    }

    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"토론 전체 내용:\n{json.dumps(debate_context, ensure_ascii=False, indent=2)}"},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
