from openai import OpenAI
import os, json, re

SYSTEM_PROMPT = """당신은 최종 검증 에이전트(Claude)입니다.
Scout, Budget, Experience 에이전트의 토론 결과를 종합해서 최적의 서울 나들이 코스를 확정하세요.
반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "final_course": [{"order": 1, "place": "장소명", "category": "카테고리", "address": "주소", "estimated_cost": 숫자}],
  "total_cost": 숫자,
  "verdict": "최종 판단 근거",
  "debate_summary": "토론 요약"
}"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if not text:
        return {"final_course": [], "total_cost": 0, "verdict": "", "debate_summary": ""}
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
        return {"final_course": [], "total_cost": 0, "verdict": "", "debate_summary": ""}


def verify(plan: dict, candidates: list, budget_result: dict, vibe_result: dict) -> dict:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    debate_context = {
        "original_plan": plan,
        "scout_candidates": candidates,
        "budget_evaluation": budget_result,
        "vibe_evaluation": vibe_result,
    }
    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"토론 전체 내용:\n{json.dumps(debate_context, ensure_ascii=False, indent=2)}"},
        ],
        max_tokens=600,
    )
    content = response.choices[0].message.content or "{}"
    result = _parse_json(content)

    # LLM이 비용을 0으로 뱉는 경우 budget_result 데이터로 보정
    budget_per = plan.get("budget_total", 0) // max(len(plan.get("schedule", [1])), 1)
    for step in result.get("final_course", []):
        if not step.get("estimated_cost"):
            step["estimated_cost"] = budget_per

    # total_cost는 항상 코드에서 재계산 (LLM 신뢰 안 함)
    result["total_cost"] = sum(
        s.get("estimated_cost", 0) for s in result.get("final_course", [])
    )
    return result
