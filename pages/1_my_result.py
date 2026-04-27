"""내 지역 추천 — 사주 + 자미두수 + 성향 테스트 10문항 → TOP5"""
import streamlit as st, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import folium
from streamlit_folium import st_folium

from core.saju      import calculate_saju, OHAENG_META
from core.ziwei     import calculate_ziwei, apply_ziwei_correction
from core.quiz_data import QUESTIONS, calc_quiz_vector
from core.matching  import load_regions, merge_vectors, get_top5
from db.database    import save_birth, save_result

st.set_page_config(page_title="내 지역 추천 | StarPlace", page_icon="🗺️", layout="wide")

# ── 공통 CSS ─────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif;}
.step-done{background:#1a3a1a;border:1px solid #4caf50;border-radius:8px;padding:6px 10px;
  color:#4caf50;font-size:.82rem;text-align:center;}
.step-now{background:#1a2a3a;border:1px solid #7ec8e3;border-radius:8px;padding:6px 10px;
  color:#7ec8e3;font-size:.82rem;text-align:center;font-weight:700;}
.step-wait{background:#111;border:1px solid #333;border-radius:8px;padding:6px 10px;
  color:#555;font-size:.82rem;text-align:center;}
.pillar-box{background:#16213e;border:1px solid #e2c27d55;border-radius:10px;padding:14px;text-align:center;}
.rank-card{background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid #e2c27d33;
  border-radius:14px;padding:18px 22px;margin-bottom:10px;}
</style>""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("먼저 로그인해주세요.")
    st.page_link("app.py", label="홈으로", icon="🏠")
    st.stop()

user = st.session_state.user

# ── 스텝 표시 ─────────────────────────────────────────────
STEPS = ["① 생년월일시", "② 사주·자미두수", "③ 성향 테스트", "④ 결과 확인"]
step  = st.session_state.get("my_step", 0)

st.title("🗺️ 나에게 맞는 지역 찾기")
cols = st.columns(4)
for i,(col,s) in enumerate(zip(cols, STEPS)):
    with col:
        css = "step-done" if i<step else ("step-now" if i==step else "step-wait")
        prefix = "✅ " if i<step else ("▶ " if i==step else "")
        st.markdown(f'<div class="{css}">{prefix}{s}</div>', unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════════
# STEP 0 — 생년월일시 입력
# ════════════════════════════════════════════════════
if step == 0:
    st.subheader("🎂 생년월일시를 입력해주세요")

    # 재방문 — 저장 정보 자동 불러오기
    if user.get("birth_year"):
        st.info(f"💾 저장된 정보: {user['birth_year']}년 {user['birth_month']}월 "
                f"{user['birth_day']}일 {user['birth_hour']}시 ({user.get('gender','?')})")
        if st.button("✅ 저장된 정보로 바로 시작", type="primary", use_container_width=True):
            st.session_state["birth"] = {
                "y":user["birth_year"],"m":user["birth_month"],
                "d":user["birth_day"],"h":user["birth_hour"],"g":user.get("gender","남")
            }
            st.session_state["my_step"] = 1
            st.rerun()
        st.markdown("또는 아래에서 새로 입력하세요:")

    c1,c2,c3 = st.columns(3)
    with c1: year  = st.number_input("출생 연도", 1940, 2010, 2000)
    with c2: month = st.number_input("월", 1, 12, 1)
    with c3: day   = st.number_input("일", 1, 31, 1)

    c4,c5 = st.columns(2)
    JIJI_LABELS = ["자","자","축","축","인","인","묘","묘","진","진","사","사",
                   "오","오","미","미","신","신","유","유","술","술","해","해"]
    with c4:
        hour = st.selectbox("출생 시각",list(range(24)),
               format_func=lambda x: f"{x:02d}시 ({JIJI_LABELS[x]}시)")
    with c5:
        gender = st.radio("성별", ["남","여"], horizontal=True)

    if st.button("🚀 분석 시작 →", type="primary", use_container_width=True):
        save_birth(user["id"], year, month, day, hour, gender)
        st.session_state.user = {**user,
            "birth_year":year,"birth_month":month,"birth_day":day,
            "birth_hour":hour,"gender":gender}
        st.session_state["birth"] = {"y":year,"m":month,"d":day,"h":hour,"g":gender}
        st.session_state["my_step"] = 1
        st.rerun()

# ════════════════════════════════════════════════════
# STEP 1 — 사주 + 자미두수 분석 결과
# ════════════════════════════════════════════════════
elif step == 1:
    b = st.session_state["birth"]
    with st.spinner("🔮 사주팔자를 분석하는 중..."):
        saju  = calculate_saju(b["y"],b["m"],b["d"],b["h"],b["g"])
        ziwei = calculate_ziwei(b["m"],b["h"])
        z_vec = apply_ziwei_correction(saju["오행비율"], ziwei)

    st.session_state.update({"saju":saju,"ziwei":ziwei,"z_vec":z_vec})

    # ── 사주 사주패 ───────────────────────────────────
    st.subheader("🔮 사주팔자 (四柱八字)")
    PILLAR_EMOJI = ["🌿","🌸","☀️","🌙"]
    cols = st.columns(4)
    for i,(col,p) in enumerate(zip(cols,saju["pillars"])):
        with col:
            st.markdown(f"""
            <div class="pillar-box">
              <div style="color:#a8b8d8;font-size:.75rem">{PILLAR_EMOJI[i]} {p['주']}</div>
              <div style="color:#e2c27d;font-size:2rem;font-weight:900;line-height:1.2">{p['천간']}</div>
              <div style="color:#7ec8e3;font-size:1.6rem;font-weight:700">{p['지지']}</div>
            </div>""", unsafe_allow_html=True)

    # ── 오행 비율 바 ─────────────────────────────────
    st.markdown("---")
    st.subheader("🌈 오행(五行) 비율")
    for oh, ratio in sorted(saju["오행비율"].items(), key=lambda x:x[1], reverse=True):
        m = OHAENG_META[oh]
        pct = int(ratio*100)
        c1,c2,c3 = st.columns([1,4,1])
        with c1: st.markdown(f"**{m['emoji']} {oh}**")
        with c2: st.progress(ratio, text=m["keyword"])
        with c3: st.markdown(f"**{pct}%**")

    # ── 자미두수 명궁 ────────────────────────────────
    st.markdown("---")
    st.subheader("🌟 자미두수 명궁 (命宮)")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1040,#0d2137);border-left:4px solid #e2c27d;
      border-radius:10px;padding:20px;margin-bottom:10px;">
      <div style="color:#e2c27d;font-size:1.15rem;font-weight:700">
        {ziwei['명궁지지']}궁 · {ziwei['주성']}
      </div>
      <div style="color:#a8b8d8;margin-top:8px">강점: {ziwei['강점']}</div>
      <div style="margin-top:8px">{"  ".join([f'<span style="background:#1a3050;border-radius:20px;padding:3px 12px;color:#7ec8e3;font-size:.82rem">{t}</span>' for t in ziwei['성격']])}</div>
    </div>""", unsafe_allow_html=True)

    if st.button("다음: 성향 테스트 →", type="primary", use_container_width=True):
        st.session_state["my_step"] = 2
        st.session_state["q_idx"]   = 0
        st.session_state["q_ans"]   = []
        st.rerun()

# ════════════════════════════════════════════════════
# STEP 2 — 성향 테스트 10문항
# ════════════════════════════════════════════════════
elif step == 2:
    q_idx = st.session_state.get("q_idx", 0)
    q_ans = st.session_state.get("q_ans", [])

    if q_idx < len(QUESTIONS):
        q = QUESTIONS[q_idx]
        prog = q_idx / len(QUESTIONS)

        st.progress(prog, text=f"문항 {q_idx+1} / {len(QUESTIONS)}")
        st.markdown(f"### {q['emoji']} {q['question']}")

        choice = st.radio("선택하세요", range(len(q["options"])),
                          format_func=lambda i: q["options"][i]["text"],
                          key=f"q{q_idx}", label_visibility="collapsed")

        c1, c2 = st.columns([1,1])
        with c1:
            if q_idx > 0 and st.button("← 이전"):
                st.session_state["q_idx"] = q_idx - 1
                if q_ans: st.session_state["q_ans"] = q_ans[:-1]
                st.rerun()
        with c2:
            if st.button("다음 →", type="primary", use_container_width=True):
                q_ans.append(choice)
                st.session_state["q_ans"] = q_ans
                st.session_state["q_idx"] = q_idx + 1
                st.rerun()
    else:
        quiz_vec = calc_quiz_vector(q_ans)
        st.session_state["quiz_vec"] = quiz_vec
        st.session_state["my_step"] = 3
        st.rerun()

# ════════════════════════════════════════════════════
# STEP 3 — TOP5 결과 + 지도
# ════════════════════════════════════════════════════
elif step == 3:
    saju     = st.session_state["saju"]
    z_vec    = st.session_state["z_vec"]
    quiz_vec = st.session_state["quiz_vec"]

    final_vec = merge_vectors(saju["오행비율"], quiz_vec, z_vec)
    regions   = load_regions()
    top5      = get_top5(final_vec, regions)

    st.session_state["my_top5"]   = top5
    st.session_state["final_vec"] = final_vec

    save_result(user["id"], top5[0]["region"], top5[0]["country"],
                top5[0]["score"], json.dumps(final_vec, ensure_ascii=False))

    # ── 오행 요약 태그 ────────────────────────────────
    st.markdown("## 🌍 나에게 맞는 지역 TOP 5")
    oh_sorted = sorted(final_vec.items(), key=lambda x:x[1], reverse=True)
    OH_BG     = {"목":"#1a3a1a","화":"#3a1a1a","토":"#2a2010","금":"#1a1a2a","수":"#0a1a2a"}
    OH_BORDER = {"목":"#4caf50","화":"#f44336","토":"#ff9800","금":"#9e9e9e","수":"#2196f3"}
    OH_EMOJI  = {"목":"🌿","화":"🔥","토":"🏔️","금":"⚙️","수":"💧"}
    tags = "".join([
        f'<span style="background:{OH_BG[oh]};border:1px solid {OH_BORDER[oh]};'
        f'border-radius:20px;padding:4px 14px;color:#fff;font-size:.82rem;margin:3px;display:inline-block">'
        f'{OH_EMOJI[oh]} {oh} {int(v*100)}%</span>'
        for oh,v in oh_sorted[:3]])
    st.markdown(f'<div style="margin-bottom:16px">나의 주요 오행: {tags}</div>',
                unsafe_allow_html=True)

    # ── TOP5 카드 ─────────────────────────────────────
    MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    RANK_COLOR = ["#e2c27d","#c0c0c0","#cd7f32","#a8b8d8","#a8b8d8"]

    for i, r in enumerate(top5):
        with st.expander(
            f"{MEDALS[i]}  **{r['region']}**, {r['country']}  —  유사도 {r['score']}%",
            expanded=(i == 0)
        ):
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"*{r['설명']}*")
                trait_html = " ".join([
                    f'<span style="background:#1a2a3a;border-radius:20px;padding:3px 10px;'
                    f'color:#7ec8e3;font-size:.8rem">{t}</span>' for t in r["특성"]])
                st.markdown(f'<div style="margin:6px 0">{trait_html}</div>', unsafe_allow_html=True)
                st.caption(f"🌤 기후: {r['기후']}  |  👥 인구밀도: {r['인구밀도']}  |  🌿 자연도: {int(r['자연도']*100)}%")
            with col2:
                st.markdown(f"""
                <div style="background:#0d1a2a;border:2px solid {RANK_COLOR[i]};border-radius:12px;
                  padding:14px;text-align:center;">
                  <div style="color:{RANK_COLOR[i]};font-size:2rem;font-weight:900">{r['score']}%</div>
                  <div style="color:#a8b8d8;font-size:.75rem">오행 유사도</div>
                </div>""", unsafe_allow_html=True)

    # ── 지도 ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("📍 TOP 5 지역 지도")
    m = folium.Map(location=[top5[0]["lat"], top5[0]["lng"]],
                   zoom_start=2, tiles="CartoDB dark_matter")
    ICON_COLORS = ["red","blue","green","purple","orange"]
    for i, r in enumerate(top5):
        folium.Marker(
            [r["lat"], r["lng"]],
            popup=folium.Popup(
                f"<b>{MEDALS[i]} {r['region']}</b><br>{r['country']}<br>유사도 {r['score']}%",
                max_width=200),
            tooltip=f"{MEDALS[i]} {r['region']}",
            icon=folium.Icon(color=ICON_COLORS[i], icon="star", prefix="fa")
        ).add_to(m)
    st_folium(m, width=None, height=460, returned_objects=[])

    # ── 하단 버튼 ────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 다시 분석하기"):
            for k in ["my_step","birth","saju","ziwei","z_vec",
                      "quiz_vec","q_idx","q_ans","my_top5","final_vec"]:
                st.session_state.pop(k, None)
            st.rerun()
    with c2:
        if st.button("💑 지역 궁합 보기 →", type="primary", use_container_width=True):
            st.switch_page("pages/2_compatibility.py")
