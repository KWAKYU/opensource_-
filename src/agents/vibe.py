from openai import OpenAI
from src.naver_api import get_vibes_for_candidates
import os, json, re

SYSTEM_PROMPT = """당신은 코스 경험 평가 에이전트(Experience)입니다.
추천 코스를 실제 방문자 관점에서 냉정하게 평가하세요. 좋은 점만 말하지 말고, 문제가 있으면 반드시 지적하세요.

[평가 항목 — 각각 구체적으로 판단]
1. 동선 효율: 장소 간 이동이 자연스러운가? 같은 방향인가, 역방향 이동이 있는가?
2. 테마 일치: 사용자가 원한 테마와 각 장소가 실제로 맞는가? 겉만 맞고 속은 다른 곳은 없는가?
3. 분위기/퀄리티: 네이버 블로그 후기 데이터를 근거로 — 후기가 적거나 평범하다면 점수에 반영할 것
4. 코스 흐름: 식사→디저트→활동처럼 자연스러운 하루 흐름인가? 어색한 순서가 있는가?
5. 다양성: 비슷한 장소가 연속되지 않는가?

[점수 기준]
- 9~10: 모든 기준 충족, 강력 추천
- 7~8: 대체로 좋으나 1~2가지 아쉬운 점 있음
- 5~6: 문제가 있어 재검토 필요
- 4 이하: 코스 재구성 요청

[objection 작성 원칙]
- 문제가 있으면 반드시 objection에 명확하게 쓸 것 (null로 두지 말 것)
- "좀 아쉽다" 같은 모호한 표현 금지, "○○ 장소는 후기가 거의 없어 품질을 보장할 수 없음" 같이 구체적으로

반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{"score": 8, "feedback": "코스 전체 평가 (구체적으로)", "objection": "문제점 또는 null", "alternative": null}"""


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

    # 네이버 블로그에서 분위기 후기 수집
    print("    [네이버 블로그] 분위기 후기 검색 중...")
    vibe_data = get_vibes_for_candidates(candidates)
    vibe_context = ""
    if vibe_data:
        vibe_context = "\n\n[네이버 블로그 분위기 후기]\n" + "\n".join(
            f"- {name}: {info}" for name, info in vibe_data.items()
        )
        print(f"    [네이버 블로그] {len(vibe_data)}개 장소 후기 수집 완료")
    else:
        print("    [네이버 블로그] 분위기 후기 없음")

    user_content = (
        f"코스 테마: {plan.get('theme', '')}\n"
        f"코스: {json.dumps(candidates, ensure_ascii=False)}\n"
        f"예산 평가: {json.dumps(budget_result, ensure_ascii=False)}"
        f"{vibe_context}"
    )

    response = client.chat.completions.create(
        model="google/gemma-3-27b-it",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content or "{}"
    return _parse_json(content)
