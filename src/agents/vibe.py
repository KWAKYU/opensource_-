from openai import OpenAI
from src.naver_api import get_vibes_for_candidates
import os, json, re

SYSTEM_PROMPT = """당신은 코스 경험 평가 에이전트입니다.
추천된 코스의 흐름, 동선, 테마 일치도를 평가하고 실제 방문자 후기 기반으로 분위기를 검토하세요.

[평가 기준]
- 동선: 장소 간 이동 거리/효율성
- 테마 일치도: 사용자가 원하는 테마와 얼마나 맞는지
- 분위기: 네이버 블로그 후기에서 수집한 실제 방문자 반응
- 다양성: 코스가 단조롭지 않은지 (카페만 3곳 등 지양)

코스에 문제가 있으면 objection에 구체적 이유를 명시하세요.
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
