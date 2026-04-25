import streamlit as st
import json
import os
import pandas as pd
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
    os.environ.setdefault("KAKAO_API_KEY", st.secrets["KAKAO_API_KEY"])
    os.environ.setdefault("NAVER_CLIENT_ID", st.secrets.get("NAVER_CLIENT_ID", ""))
    os.environ.setdefault("NAVER_CLIENT_SECRET", st.secrets.get("NAVER_CLIENT_SECRET", ""))
except Exception:
    pass

from src.agents.planner import plan
from src.agents.scout import scout, scout_one
from src.agents.budget import evaluate_budget
from src.agents.vibe import evaluate_vibe
from src.agents.verifier import verify

# ── 카테고리 아이콘 ──────────────────────────────
CATEGORY_ICON = {
    "카페": "☕", "체인카페": "🏪", "맛집": "🍽️", "패스트푸드": "🍔",
    "디저트": "🍰", "방탈출": "🔐", "공방·체험": "🎨", "액티비티": "🎳",
    "문화·전시": "🖼️", "포토스팟": "📸", "쇼핑": "🛍️", "바·주점": "🍺", "공원·자연": "🌿",
}

st.set_page_config(page_title="서울 코스 추천기", page_icon="🗺️", layout="centered")
st.title("🗺️ 서울 코스 추천기")
st.caption("AI 에이전트들이 서로 토론해서 최적의 나들이 코스를 추천해드립니다")
st.divider()

# ── 입력 UI ──────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    location = st.text_input("📍 지역", placeholder="홍대, 강남, 이태원, 성수동...")
    people = st.number_input("👥 인원", min_value=1, max_value=10, value=2)
with col2:
    budget = st.number_input("💰 예산 (원)", min_value=10000, max_value=1000000, value=50000, step=10000)
    theme = st.selectbox("🎯 테마", ["맛집 투어", "카페 투어", "문화/예술", "포토스팟", "힐링", "액티비티", "쇼핑"])

duration = st.select_slider("⏱️ 소요 시간", options=["2시간", "반나절", "하루 종일"], value="반나절")
col3, col4 = st.columns(2)
with col3:
    allow_chains = st.checkbox("🏪 체인점 포함 (스타벅스, 메가커피, 맥도날드 등)", value=False)
with col4:
    extra = st.text_input("기타 요청 (선택)", placeholder="대중교통 이용, 실내 위주, 영어 메뉴 있는 곳...")

run = st.button("🤖 코스 추천받기", use_container_width=True, type="primary")


# ── 토론 실행 함수 ────────────────────────────────
def run_debate(user_input, initial_plan, exclude_places=None):
    debate_log = []
    candidates = []
    budget_result = {}
    vibe_result = {}

    st.subheader("🤖 에이전트 토론 과정")

    with st.status("🧠 Planner (Claude) — 코스 전략 수립 중...", expanded=True) as s:
        st.json(initial_plan)
        s.update(label="✅ Planner — 전략 확정", state="complete")

    for round_num in range(1, 6):
        st.markdown(f"**— Round {round_num} —**")

        with st.status(f"🔍 Scout (Gemma) — 장소 탐색 중...", expanded=False) as s:
            candidates = scout(initial_plan, exclude_places=exclude_places)
            st.write(f"{len(candidates)}개 장소 발견")
            for c in candidates:
                st.write(f"• **{c.get('name', '')}** — {c.get('address', '')}")
                st.caption(f"  추천 이유: {c.get('reason', '')}")
            debate_log.append({"round": round_num, "agent": "Scout", "result": candidates})
            s.update(label=f"✅ Scout — {len(candidates)}개 장소 발견", state="complete")

        with st.status(f"💰 Budget (Perplexity) — 예산 검토 중...", expanded=False) as s:
            budget_result = evaluate_budget(initial_plan, candidates)
            approved = budget_result.get("approved", False)
            total = budget_result.get("total_estimated", 0)
            st.write(f"예상 비용: **{total:,}원** / 예산: {budget:,}원")
            st.write(f"의견: {budget_result.get('suggestion', '')}")
            debate_log.append({"round": round_num, "agent": "Budget", "result": budget_result})
            icon = "✅" if approved else "⚠️"
            s.update(label=f"{icon} Budget — {'승인' if approved else '예산 초과'} ({total:,}원)", state="complete")

        with st.status(f"✨ Experience (Gemma) — 코스 평가 중...", expanded=False) as s:
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

        if round_num >= 2 and approved and score >= 7:
            st.success(f"✅ Round {round_num}에서 합의 완료!")
            break
        elif round_num < 5:
            st.warning("합의 미달 → 재토론")

    with st.status("🏆 Verifier (Claude Haiku) — 최종 검증 중...", expanded=False) as s:
        final = verify(initial_plan, candidates, budget_result, vibe_result)
        s.update(label="✅ Verifier — 최종 코스 확정", state="complete")

    return {"plan": initial_plan, "candidates": candidates,
            "budget": budget_result, "vibe": vibe_result,
            "final": final, "debate_log": debate_log}


# ── 결과 표시 함수 ────────────────────────────────
def show_results(result, budget_input, location_input):
    final = result["final"]
    candidates = result["candidates"]

    st.divider()
    st.subheader(f"📍 {location_input} 추천 코스")

    # 지도
    course_coords = [
        {"lat": c.get("lat"), "lon": c.get("lng")}
        for c in candidates if c.get("lat") and c.get("lng")
    ]
    if course_coords:
        map_df = pd.DataFrame(course_coords)
        st.map(map_df, latitude="lat", longitude="lon", size=80, color="#00B4D8")

    # 전체 리롤 버튼
    col_r1, col_r2 = st.columns([1, 3])
    with col_r1:
        if st.button("🔀 전체 리롤", use_container_width=True):
            used = st.session_state.get("used_places", set())
            used.update(s.get("place", "") for s in final.get("final_course", []))
            st.session_state["used_places"] = used
            st.session_state["do_full_reroll"] = True
            st.rerun()

    # 장소별 카드 + 개별 리롤
    course = final.get("final_course", [])
    for i, step in enumerate(course):
        place_name = step.get("place", "")
        address    = step.get("address", "")
        category   = step.get("category", "")
        icon       = CATEGORY_ICON.get(category, "📍")
        naver_url  = f"https://map.naver.com/v5/search/{quote(place_name)}"

        with st.container(border=True):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            with col_a:
                st.markdown(f"**{step.get('order', i+1)}. {place_name}**")
                st.caption(f"{icon} {category}  |  📍 {address}")
                st.markdown(f"[🗺️ 네이버 지도에서 보기]({naver_url})")
            with col_b:
                cost = step.get('estimated_cost', 0)
                st.markdown(f"**예상 비용**")
                st.markdown(f"### {cost:,}원")
            with col_c:
                if st.button("🔄 리롤", key=f"reroll_{i}"):
                    used = st.session_state.get("used_places", set())
                    used.add(place_name)
                    st.session_state["used_places"] = used
                    st.session_state["reroll_idx"] = i
                    st.session_state["reroll_category"] = category
                    st.rerun()

    col_total, col_remain = st.columns(2)
    total_cost = final.get("total_cost", 0)
    with col_total:
        st.metric("총 예상 비용", f"{total_cost:,}원")
    with col_remain:
        st.metric("남은 예산", f"{budget_input - total_cost:,}원")

    with st.expander("💬 토론 요약 보기"):
        st.write(final.get("debate_summary", ""))
        st.info(f"**판단 근거**: {final.get('verdict', '')}")

    with st.expander("🗂️ 전체 토론 로그 (JSON)"):
        st.json({"plan": result["plan"], "debate_log": result["debate_log"], "final": final})


# ── 메인 로직 ─────────────────────────────────────
if run:
    if not location:
        st.error("지역을 입력해주세요.")
        st.stop()

    user_input = f"{location}, {people}명, 예산 {budget}원, {theme}, {duration}"
    if not allow_chains:
        user_input += ", 체인점 제외 (스타벅스·메가커피·이디야·컴포즈·맥도날드·버거킹·KFC·파리바게뜨 등 프랜차이즈 제외, 독립 로컬 매장만)"
    if extra:
        user_input += f", {extra}"

    st.session_state["user_input"] = user_input
    st.session_state["location"]   = location
    st.session_state["budget"]     = budget
    st.session_state["used_places"] = set()
    st.session_state.pop("do_full_reroll", None)
    st.session_state.pop("reroll_idx", None)

    initial_plan = plan(user_input)
    st.session_state["initial_plan"] = initial_plan

    result = run_debate(user_input, initial_plan)
    st.session_state["result"] = result
    show_results(result, budget, location)

# 전체 리롤
elif st.session_state.get("do_full_reroll"):
    st.session_state.pop("do_full_reroll")
    used = st.session_state.get("used_places", set())
    initial_plan = st.session_state["initial_plan"]
    user_input   = st.session_state["user_input"]
    budget_val   = st.session_state["budget"]
    location_val = st.session_state["location"]

    result = run_debate(user_input, initial_plan, exclude_places=list(used))
    st.session_state["result"] = result
    show_results(result, budget_val, location_val)

# 개별 리롤
elif st.session_state.get("reroll_idx") is not None:
    idx      = st.session_state.pop("reroll_idx")
    category = st.session_state.pop("reroll_category", "")
    used     = st.session_state.get("used_places", set())
    result   = st.session_state["result"]
    initial_plan = st.session_state["initial_plan"]
    budget_val   = st.session_state["budget"]
    location_val = st.session_state["location"]

    with st.status(f"🔄 {category} 장소 리롤 중...", expanded=True) as s:
        new_place = scout_one(initial_plan, category, exclude_places=list(used))
        if new_place:
            course = result["final"]["final_course"]
            old_name = course[idx].get("place", "")
            course[idx] = {
                "order": idx + 1,
                "place": new_place.get("name", old_name),
                "category": new_place.get("category", category),
                "address": new_place.get("address", ""),
                "estimated_cost": course[idx].get("estimated_cost", 0),
            }
            # candidates 좌표도 업데이트
            if idx < len(result["candidates"]):
                result["candidates"][idx] = new_place
            s.update(label=f"✅ {new_place.get('name', '')}로 교체 완료!", state="complete")
        else:
            s.update(label="⚠️ 새 장소를 찾지 못했어요", state="error")

    st.session_state["result"] = result
    show_results(result, budget_val, location_val)

# 이전 결과 유지 표시
elif "result" in st.session_state:
    show_results(
        st.session_state["result"],
        st.session_state.get("budget", budget),
        st.session_state.get("location", location),
    )
