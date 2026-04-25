from src.agents.planner import plan
from src.agents.scout import scout
from src.agents.budget import evaluate_budget
from src.agents.vibe import evaluate_vibe
from src.agents.verifier import verify
import json


def run_debate(user_input: str, max_rounds: int = 3) -> dict:
    print(f"\n{'='*50}")
    print(f"[PLANNER] 요청 분석 중...")
    initial_plan = plan(user_input)
    print(f"[PLANNER] 플랜 확정: {json.dumps(initial_plan, ensure_ascii=False)}")

    debate_log = []
    candidates = []
    budget_result = {}
    vibe_result = {}

    for round_num in range(1, max_rounds + 1):
        print(f"\n--- Round {round_num} ---")

        print(f"[SCOUT] 장소 탐색 중...")
        candidates = scout(initial_plan)
        print(f"[SCOUT] {len(candidates)}개 후보 발견")
        debate_log.append({"round": round_num, "agent": "Scout", "result": candidates})

        print(f"[BUDGET] 예산 검토 중...")
        budget_result = evaluate_budget(initial_plan, candidates)
        print(f"[BUDGET] 승인: {budget_result.get('approved')} | 예상 비용: {budget_result.get('total_estimated')}원")
        debate_log.append({"round": round_num, "agent": "Budget", "result": budget_result})

        print(f"[VIBE] 분위기 평가 중...")
        vibe_result = evaluate_vibe(initial_plan, candidates, budget_result)
        print(f"[VIBE] 점수: {vibe_result.get('score')}/10 | {vibe_result.get('feedback')}")
        debate_log.append({"round": round_num, "agent": "Vibe", "result": vibe_result})

        # 예산 통과 + 분위기 7점 이상이면 조기 종료
        if budget_result.get("approved") and vibe_result.get("score", 0) >= 7:
            print(f"\n[DEBATE] Round {round_num}에서 합의 완료")
            break

        # 다음 라운드를 위해 플랜 보정
        if not budget_result.get("approved"):
            print(f"[DEBATE] 예산 초과 → 재조정")
        if vibe_result.get("score", 0) < 7:
            print(f"[DEBATE] 분위기 점수 부족 → 재탐색")

    print(f"\n[VERIFIER] 최종 검증 중 (Claude)...")
    final = verify(initial_plan, candidates, budget_result, vibe_result)
    print(f"[VERIFIER] 코스 확정 완료")

    return {
        "input": user_input,
        "plan": initial_plan,
        "debate_rounds": len(debate_log) // 3,
        "debate_log": debate_log,
        "final": final,
    }
