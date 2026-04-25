from openai import OpenAI
from src.agents.budget import CATEGORY_COST
import os, json, re

# 이름에 이 단어가 있으면 무조건 맛집 (포토스팟/쇼핑 등으로 오분류 방지)
FOOD_NAME_KEYWORDS = [
    "식당", "음식점", "육회", "연어", "초밥", "스시", "삼겹", "갈비", "치킨", "돈까스",
    "라멘", "우동", "파스타", "피자", "버거", "국밥", "설렁탕", "곱창", "떡볶이",
    "냉면", "쌀국수", "보쌈", "족발", "샤부", "오마카세", "이자카야", "주점",
    "불판", "구이", "찜", "탕", "전골", "정식",
]

# 반나절/하루종일별 카테고리 최대 허용 횟수
MAX_CATEGORY_COUNT = {
    "2시간":    {"맛집": 1, "카페": 1, "디저트": 1},
    "반나절":   {"맛집": 1, "카페": 2, "디저트": 1},
    "하루 종일": {"맛집": 2, "카페": 2, "디저트": 1},
}


def _sanitize_course(course: list, duration: str) -> list:
    """LLM 오류 교정: 음식점 오분류 수정 + 카테고리 중복 초과 제거"""
    limits = MAX_CATEGORY_COUNT.get(duration, MAX_CATEGORY_COUNT["반나절"])
    counts: dict = {}
    fixed = []

    for step in course:
        name = step.get("place", "")
        cat = step.get("category", "")

        # 1. 음식 키워드 포함인데 맛집 아닌 카테고리로 분류된 경우 → 맛집으로 강제 수정
        if any(k in name for k in FOOD_NAME_KEYWORDS) and cat not in ("맛집", "패스트푸드", "바·주점"):
            cat = "맛집"
            step = {**step, "category": "맛집",
                    "estimated_cost": max(step.get("estimated_cost", 0), CATEGORY_COST["맛집"])}

        # 2. 카테고리 허용 횟수 초과 시 제거
        limit = limits.get(cat, 99)
        if counts.get(cat, 0) >= limit:
            continue

        counts[cat] = counts.get(cat, 0) + 1
        fixed.append(step)

    # 순서 재부여
    for i, step in enumerate(fixed):
        step["order"] = i + 1

    return fixed

SYSTEM_PROMPT = """당신은 최종 검증 에이전트(Claude)입니다.
Scout, Budget, Experience 에이전트의 토론 결과를 종합해서 최적의 서울 나들이 코스를 확정하세요.

[최종 확정 기준]
1. Experience 에이전트의 점수가 낮거나 objection이 있었던 장소는 제외하고 더 나은 후보로 대체
2. Budget 에이전트가 예산 초과 지적한 장소는 비용 조정 또는 교체
3. 동선이 자연스럽도록 순서 최적화 (멀리 돌아가는 구조면 순서 변경)
4. 같은 카테고리 연속 배치 금지 — 카페→카페, 맛집→맛집 절대 불가
5. 각 장소의 estimated_cost는 반드시 실제 1인 기준 현실적 금액 (카페 최소 7,000원, 맛집 최소 12,000원)

[verdict 작성 원칙]
- 왜 이 코스를 최종 확정했는지 구체적으로 서술
- 어떤 장소가 제외/교체되었고 그 이유는 무엇인지 포함
- "좋은 코스입니다" 같은 모호한 표현 금지

반드시 아래 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "final_course": [{"order": 1, "place": "장소명", "category": "카테고리", "address": "주소", "estimated_cost": 숫자}],
  "total_cost": 숫자,
  "verdict": "최종 판단 근거 (구체적으로)",
  "debate_summary": "라운드별 토론 핵심 쟁점 요약"
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
        max_tokens=1200,
    )
    content = response.choices[0].message.content or "{}"
    result = _parse_json(content)

    # final_course가 비어있으면 candidates로 직접 구성
    if not result.get("final_course") and candidates:
        result["final_course"] = [
            {
                "order": i + 1,
                "place": c.get("name", ""),
                "category": c.get("category", ""),
                "address": c.get("address", ""),
                "estimated_cost": CATEGORY_COST.get(c.get("category", ""), 10000),
            }
            for i, c in enumerate(candidates)
        ]

    # estimated_cost가 0이면 카테고리별 단가로 채우기
    for step in result.get("final_course", []):
        if not step.get("estimated_cost"):
            step["estimated_cost"] = CATEGORY_COST.get(step.get("category", ""), 10000)

    # 음식점 오분류 + 카테고리 중복 초과 Python 레벨 교정
    duration = plan.get("duration", "반나절")
    result["final_course"] = _sanitize_course(result.get("final_course", []), duration)

    # total_cost는 항상 코드에서 재계산
    result["total_cost"] = sum(
        s.get("estimated_cost", 0) for s in result.get("final_course", [])
    )
    return result
