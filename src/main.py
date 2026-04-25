import os
from dotenv import load_dotenv
from src.debate import run_debate
import json

load_dotenv()


def main():
    print("=== AI 데이트 플래너 (멀티에이전트 토론) ===")
    print("예시: 강남, 2인, 예산 10만원, 저녁 데이트")
    print()

    user_input = input("데이트 조건을 입력하세요: ").strip()
    if not user_input:
        user_input = "강남, 2인, 예산 10만원, 저녁 데이트"

    result = run_debate(user_input)

    print(f"\n{'='*50}")
    print("최종 데이트 코스")
    print('='*50)
    final = result["final"]
    for step in final.get("final_course", []):
        print(f"{step['order']}. {step['place']} ({step['category']})")
        print(f"   주소: {step['address']}")
        print(f"   예상 비용: {step['estimated_cost']:,}원")
        print()
    print(f"총 예상 비용: {final.get('total_cost', 0):,}원")
    print(f"\n[토론 요약] {final.get('debate_summary', '')}")
    print(f"[판단 근거] {final.get('verdict', '')}")

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n결과가 result.json에 저장되었습니다.")


if __name__ == "__main__":
    main()
