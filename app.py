import streamlit as st
import json
import os
from dotenv import load_dotenv

# 로컬: .env 파일 / Streamlit Cloud: st.secrets 자동 사용
load_dotenv()
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
    os.environ.setdefault("KAKAO_API_KEY", st.secrets["KAKAO_API_KEY"])
except Exception:
    pass  # 로컬 환경에서는 .env 사용

from src.agents.planner import plan
from src.agents.scout import scout
from src.agents.budget import evaluate_budget
from src.agents.vibe import evaluate_vibe
from src.agents.verifier import verify

st.set_page_config(page_title="서울 코스 추천기", page_icon="🗺️", layout="centered")

st.title("🗺️ 서울 코스 추천기")
st.caption("AI 에이전트들이 서로 토론해서 최적의 나들이 코스를 추천해드립니다")

st.divider()

col1, col2 = st.columns(2)
with col1:
    location = st.text_input("📍 지역", placeholder="홍대, 강남, 이태원, 성수동...")
    people = st.number_input("👥 인원", min_value=1, max_value=10, value=2)
with col2:
    budget = st.number_input("💰 예산 (원)", min_value=10000, max_value=1000000, value=50000, step=10000)
    theme = st.selectbox("🎯 테마", ["맛집 투어", "카페 투어", "문화/예술", "포토스팟", "힐링", "액티비티", "쇼핑"])

duration = st.select_slider("⏱️ 소요 시간", options=["2시간", "반나절", "하루 종일"], value="반나절")
extra = st.text_input("기타 요청 (선택)", placeholder="대중교통 이용, 실내 위주, 영어 메뉴 있는 곳...")

run = st.button("🤖 코스 추천받기", use_container_width=True, type="primary")

if run:
    if not location:
        st.error("지역을 입력해주세요.")
        st.stop()

    user_input = f"{location}, {people}명, 예산 {budget}원, {theme}, {duration}"
    if extra:
        user_input += f", {extra}"

    st.divider()
    st.subheader("🤖 에이전트 토론 과정")

    with st.status("🧠 Planner (Claude) — 코스 전략 수립 중...", expanded=True) as s:
        initial_plan = plan(user_input)
        st.json(initial_plan)
        s.update(label="✅ Planner — 전략 확정", state="complete")

    debate_log = []
    candidates = []
    budget_result = {}
    vibe_result = {}

    for round_num in range(1, 4):
        st.markdown(f"**— Round {round_num} —**")

        with st.status(f"🔍 Scout (Mixtral) — 장소 탐색 중...", expanded=False) as s:
            candidates = scout(initial_plan)
            st.write(f"{len(candidates)}개 장소 발견")
            for c in candidates:
                st.write(f"• **{c.get('name', '')}** — {c.get('address', '')}")
                st.caption(f"  추천 이유: {c.get('reason', '')}")
            debate_log.append({"round": round_num, "agent": "Scout", "result": candidates})
            s.update(label=f"✅ Scout — {len(candidates)}개 장소 발견", state="complete")

        with st.status(f"💰 Budget (DeepSeek) — 예산 검토 중...", expanded=False) as s:
            budget_result = evaluate_budget(initial_plan, candidates)
            approved = budget_result.get("approved", False)
            total = budget_result.get("total_estimated", 0)
            st.write(f"예상 비용: **{total:,}원** / 예산: {budget:,}원")
            st.write(f"의견: {budget_result.get('suggestion', '')}")
            debate_log.append({"round": round_num, "agent": "Budget", "result": budget_result})
            icon = "✅" if approved else "⚠️"
            s.update(label=f"{icon} Budget — {'승인' if approved else '예산 초과'} ({total:,}원)", state="complete")

        with st.status(f"✨ Experience (Mixtral) — 코스 평가 중...", expanded=False) as s:
            vibe_result = evaluate_vibe(initial_plan, candidates, budget_result)
            score = vibe_result.get("score", 0)
            feedback = vibe_result.get("feedback", "")
            objection = vibe_result.get("objection")
            st.write(f"점수: **{score}/10**")
            st.write(f"평가: {feedback}")
            if objection:
                st.warning(f"반박: {objection}")
            debate_log.append({"round": round_num, "agent": "Experience", "result": vibe_result})
            s.update(label=f"✅ Experience — {score}/10점", state="complete")

        if approved and score >= 7:
            st.success(f"✅ Round {round_num}에서 합의 완료!")
            break
        elif round_num < 3:
            st.warning("합의 미달 → 재토론")

    with st.status("🏆 Verifier (Claude) — 최종 검증 중...", expanded=False) as s:
        final = verify(initial_plan, candidates, budget_result, vibe_result)
        s.update(label="✅ Verifier — 최종 코스 확정", state="complete")

    st.divider()
    st.subheader(f"📍 {location} 추천 코스")

    course = final.get("final_course", [])
    for step in course:
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{step.get('order', '')}. {step.get('place', '')}**")
                st.caption(f"📂 {step.get('category', '')}  |  📍 {step.get('address', '')}")
            with col_b:
                st.metric("예상 비용", f"{step.get('estimated_cost', 0):,}원")

    col_total, col_remain = st.columns(2)
    total_cost = final.get('total_cost', 0)
    with col_total:
        st.metric("총 예상 비용", f"{total_cost:,}원")
    with col_remain:
        st.metric("남은 예산", f"{budget - total_cost:,}원")

    with st.expander("💬 토론 요약 보기"):
        st.write(final.get("debate_summary", ""))
        st.info(f"**판단 근거**: {final.get('verdict', '')}")

    with st.expander("🗂️ 전체 토론 로그 (JSON)"):
        st.json({"plan": initial_plan, "debate_log": debate_log, "final": final})
