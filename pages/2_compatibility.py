"""지역 궁합 — 두 사람 각각 사주+자미두수+성향 테스트 → 공동 TOP5"""
import streamlit as st, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import folium
from streamlit_folium import st_folium

from core.saju      import calculate_saju, OHAENG_META
from core.ziwei     import calculate_ziwei, apply_ziwei_correction
from core.quiz_data import QUESTIONS, calc_quiz_vector
from core.matching  import load_regions, merge_vectors, get_compatibility
from db.database    import get_user, save_birth

st.set_page_config(page_title="지역 궁합 | StarPlace", page_icon="💑", layout="wide")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif;}
.compat-hero{background:linear-gradient(135deg,#1a0a2e,#0a2040);border-radius:16px;
  padding:28px;text-align:center;margin-bottom:20px;}
.compat-hero h2{color:#e2c27d;margin:0;}
.person-card{background:#16213e;border:1px solid #e2c27d44;border-radius:12px;padding:16px;margin-bottom:8px;}
.step-now{background:#1a2a3a;border:1px solid #7ec8e3;border-radius:8px;padding:6px 10px;
  color:#7ec8e3;font-size:.82rem;text-align:center;font-weight:700;}
.step-done{background:#1a3a1a;border:1px solid #4caf50;border-radius:8px;padding:6px 10px;
  color:#4caf50;font-size:.82rem;text-align:center;}
.step-wait{background:#111;border:1px solid #333;border-radius:8px;padding:6px 10px;
  color:#555;font-size:.82rem;text-align:center;}
</style>""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    st.warning("먼저 로그인해주세요.")
    st.page_link("app.py", label="홈으로", icon="🏠")
    st.stop()

user = st.session_state.user

st.markdown("""<div class="compat-hero">
  <h2>💑 지역 궁합</h2>
  <p style="color:#a8b8d8">두 사람이 함께 살기 가장 좋은 도시는 어디일까요?</p>
</div>""", unsafe_allow_html=True)

# ── 궁합 스텝 관리 ────────────────────────────────────────
# 0: 사람1 생년월일시  1: 사람1 사주/자미두수 확인
# 2: 사람1 성향테스트  3: 사람2 생년월일시
# 4: 사람2 사주/자미두수 확인  5: 사람2 성향테스트
# 6: 궁합 결과

compat_step = st.session_state.get("compat_step", 0)

STEP_LABELS = [
    "① 사람1 생년월일",
    "② 사람1 사주확인",
    "③ 사람1 성향테스트",
    "④ 사람2 생년월일",
    "⑤ 사람2 사주확인",
    "⑥ 사람2 성향테스트",
    "⑦ 궁합 결과",
]

cols = st.columns(7)
for i,(col,lbl) in enumerate(zip(cols, STEP_LABELS)):
    with col:
        css = "step-done" if i < compat_step else ("step-now" if i == compat_step else "step-wait")
        st.markdown(f'<div class="{css}">{lbl}</div>', unsafe_allow_html=True)

st.markdown("---")

JIJI_LABELS = ["자","자","축","축","인","인","묘","묘","진","진","사","사",
               "오","오","미","미","신","신","유","유","술","술","해","해"]

# ════ 공통 서브 루틴 ══════════════════════════════════════
def birth_input_form(person_label:str, key_prefix:str, saved_user:dict=None):
    """생년월일시 입력 폼. 반환: dict or None"""
    st.subheader(f"🎂 {person_label} 생년월일시")

    if saved_user and saved_user.get("birth_year"):
        st.info(f"💾 저장 정보: {saved_user['birth_year']}년 {saved_user['birth_month']}월 "
                f"{saved_user['birth_day']}일 {saved_user['birth_hour']}시")
        if st.button(f"✅ {person_label} 저장 정보 사용", type="primary",
                     key=f"{key_prefix}_use_saved"):
            return {"y":saved_user["birth_year"],"m":saved_user["birth_month"],
                    "d":saved_user["birth_day"],"h":saved_user["birth_hour"],
                    "g":saved_user.get("gender","남"),"name":saved_user.get("nickname",person_label)}
        st.markdown("또는 직접 입력:")

    c1,c2,c3 = st.columns(3)
    with c1: y = st.number_input("연도", 1940, 2010, 2000, key=f"{key_prefix}_y")
    with c2: m = st.number_input("월",   1, 12,  1,    key=f"{key_prefix}_m")
    with c3: d = st.number_input("일",   1, 31,  1,    key=f"{key_prefix}_d")
    c4,c5 = st.columns(2)
    with c4:
        h = st.selectbox("시각", list(range(24)),
                         format_func=lambda x:f"{x:02d}시 ({JIJI_LABELS[x]}시)",
                         key=f"{key_prefix}_h")
    with c5:
        g = st.radio("성별",["남","여"],horizontal=True,key=f"{key_prefix}_g")
    name = st.text_input(f"{person_label} 이름/닉네임", placeholder="예: 홍길동", key=f"{key_prefix}_name")

    if st.button(f"🚀 {person_label} 분석 시작 →", type="primary",
                 use_container_width=True, key=f"{key_prefix}_go"):
        return {"y":y,"m":m,"d":d,"h":h,"g":g,"name":name or person_label}
    return None

def saju_confirm_page(person_label:str, birth:dict, next_step:int):
    """사주/자미두수 분석 결과 확인 화면"""
    with st.spinner(f"🔮 {person_label} 사주 분석 중..."):
        saju  = calculate_saju(birth["y"],birth["m"],birth["d"],birth["h"],birth["g"])
        ziwei = calculate_ziwei(birth["m"],birth["h"])
        z_vec = apply_ziwei_correction(saju["오행비율"], ziwei)

    st.subheader(f"🔮 {person_label} — {birth.get('name',person_label)}")

    # 사주패
    PILLAR_EMOJI = ["🌿","🌸","☀️","🌙"]
    cols = st.columns(4)
    for i,(col,p) in enumerate(zip(cols,saju["pillars"])):
        with col:
            st.markdown(f"""
            <div style="background:#16213e;border:1px solid #e2c27d44;border-radius:10px;
              padding:12px;text-align:center">
              <div style="color:#a8b8d8;font-size:.72rem">{PILLAR_EMOJI[i]} {p['주']}</div>
              <div style="color:#e2c27d;font-size:1.8rem;font-weight:900">{p['천간']}</div>
              <div style="color:#7ec8e3;font-size:1.4rem;font-weight:700">{p['지지']}</div>
            </div>""", unsafe_allow_html=True)

    # 오행 간단히
    st.markdown("**오행 비율:**")
    oh_sorted = sorted(saju["오행비율"].items(), key=lambda x:x[1], reverse=True)
    tags = " ".join([
        f'<span style="background:#1a2030;border-radius:20px;padding:3px 10px;'
        f'color:#7ec8e3;font-size:.8rem">'
        f'{OHAENG_META[oh]["emoji"]} {oh} {int(v*100)}%</span>'
        for oh,v in oh_sorted])
    st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

    # 자미두수
    st.markdown(f"""
    <div style="background:#1a1040;border-left:4px solid #e2c27d;border-radius:8px;
      padding:12px 16px;margin:10px 0">
      <b style="color:#e2c27d">{ziwei['명궁지지']}궁 · {ziwei['주성']}</b>
      <div style="color:#a8b8d8;font-size:.88rem;margin-top:4px">강점: {ziwei['강점']}</div>
    </div>""", unsafe_allow_html=True)

    if st.button(f"다음: {person_label} 성향 테스트 →", type="primary",
                 use_container_width=True, key=f"next_{next_step}"):
        return saju, ziwei, z_vec
    return None, None, None

def quiz_page(person_label:str, key_prefix:str, next_step:int):
    """성향 테스트 10문항"""
    q_idx = st.session_state.get(f"{key_prefix}_q_idx", 0)
    q_ans = st.session_state.get(f"{key_prefix}_q_ans", [])

    if q_idx < len(QUESTIONS):
        q = QUESTIONS[q_idx]
        st.progress(q_idx/len(QUESTIONS), text=f"{person_label} — 문항 {q_idx+1}/{len(QUESTIONS)}")
        st.markdown(f"### {q['emoji']} {q['question']}")
        choice = st.radio("선택", range(len(q["options"])),
                          format_func=lambda i: q["options"][i]["text"],
                          key=f"{key_prefix}_q{q_idx}", label_visibility="collapsed")
        c1,c2 = st.columns(2)
        with c1:
            if q_idx>0 and st.button("← 이전", key=f"{key_prefix}_prev"):
                st.session_state[f"{key_prefix}_q_idx"] = q_idx-1
                if q_ans: st.session_state[f"{key_prefix}_q_ans"] = q_ans[:-1]
                st.rerun()
        with c2:
            if st.button("다음 →", type="primary", use_container_width=True, key=f"{key_prefix}_nxt"):
                q_ans.append(choice)
                st.session_state[f"{key_prefix}_q_ans"] = q_ans
                st.session_state[f"{key_prefix}_q_idx"] = q_idx+1
                st.rerun()
        return None
    else:
        vec = calc_quiz_vector(q_ans)
        st.session_state["compat_step"] = next_step
        return vec

# ════════════════════════════════════════════════════
# 스텝별 분기
# ════════════════════════════════════════════════════

if compat_step == 0:
    # 사람1 입력 — 나 자신 (로그인 유저) 또는 직접 입력
    st.markdown("### 👤 사람 1 정보")
    mode = st.radio("입력 방식", ["👤 내 정보 사용 (로그인 유저)", "📅 직접 입력"],
                    horizontal=True, key="p1_mode")
    if mode == "👤 내 정보 사용 (로그인 유저)":
        result = birth_input_form("사람 1", "p1", saved_user=user)
    else:
        result = birth_input_form("사람 1", "p1_manual")

    if result:
        st.session_state["p1_birth"] = result
        st.session_state["compat_step"] = 1
        st.rerun()

elif compat_step == 1:
    birth = st.session_state["p1_birth"]
    saju, ziwei, z_vec = saju_confirm_page("사람 1", birth, 2)
    if saju:
        st.session_state.update({"p1_saju":saju,"p1_ziwei":ziwei,"p1_z_vec":z_vec})
        st.session_state["compat_step"] = 2
        st.session_state["p1_q_idx"] = 0
        st.session_state["p1_q_ans"] = []
        st.rerun()

elif compat_step == 2:
    quiz_vec = quiz_page("사람 1", "p1", next_step=3)
    if quiz_vec is not None:
        st.session_state["p1_quiz_vec"] = quiz_vec
        st.session_state["compat_step"] = 3
        st.rerun()

elif compat_step == 3:
    # 사람2 입력 — 아이디 검색 or 직접 입력
    st.markdown("### 👥 사람 2 정보")
    mode2 = st.radio("입력 방식", ["🔍 StarPlace 아이디 검색", "📅 직접 입력"],
                     horizontal=True, key="p2_mode")

    other_user = None
    if mode2 == "🔍 StarPlace 아이디 검색":
        uid_search = st.text_input("상대방 아이디", placeholder="StarPlace 아이디 입력")
        if st.button("🔍 검색", key="search_uid"):
            if uid_search == user["username"]:
                st.error("본인 아이디는 입력할 수 없어요!")
            else:
                found = get_user(uid_search)
                if found and found.get("birth_year"):
                    st.session_state["p2_found_user"] = found
                    st.success(f"✅ {found['nickname']}님 정보를 불러왔어요!")
                elif found:
                    st.warning("해당 유저가 아직 생년월일시를 등록하지 않았어요.")
                else:
                    st.error("존재하지 않는 아이디입니다.")

        if st.session_state.get("p2_found_user"):
            other_user = st.session_state["p2_found_user"]

        result = birth_input_form("사람 2", "p2_search", saved_user=other_user)
    else:
        result = birth_input_form("사람 2", "p2_manual")

    if result:
        st.session_state["p2_birth"] = result
        st.session_state["compat_step"] = 4
        st.rerun()

elif compat_step == 4:
    birth = st.session_state["p2_birth"]
    saju, ziwei, z_vec = saju_confirm_page("사람 2", birth, 5)
    if saju:
        st.session_state.update({"p2_saju":saju,"p2_ziwei":ziwei,"p2_z_vec":z_vec})
        st.session_state["compat_step"] = 5
        st.session_state["p2_q_idx"] = 0
        st.session_state["p2_q_ans"] = []
        st.rerun()

elif compat_step == 5:
    quiz_vec = quiz_page("사람 2", "p2", next_step=6)
    if quiz_vec is not None:
        st.session_state["p2_quiz_vec"] = quiz_vec
        st.session_state["compat_step"] = 6
        st.rerun()

# ════════════════════════════════════════════════════
# STEP 6 — 궁합 결과
# ════════════════════════════════════════════════════
elif compat_step == 6:
    p1_name = st.session_state["p1_birth"].get("name","사람1")
    p2_name = st.session_state["p2_birth"].get("name","사람2")

    vec1 = merge_vectors(st.session_state["p1_saju"]["오행비율"],
                         st.session_state["p1_quiz_vec"],
                         st.session_state["p1_z_vec"])
    vec2 = merge_vectors(st.session_state["p2_saju"]["오행비율"],
                         st.session_state["p2_quiz_vec"],
                         st.session_state["p2_z_vec"])

    regions = load_regions()
    result  = get_compatibility(vec1, vec2, regions)
    top5    = result["top5"]

    # ── 궁합 점수 카드 ────────────────────────────────
    st.markdown("## ✨ 궁합 결과")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div style="background:#1a1040;border:2px solid #e2c27d;border-radius:14px;
          padding:20px;text-align:center">
          <div style="color:#e2c27d;font-size:2.5rem;font-weight:900">{result['점수']}점</div>
          <div style="color:#a8b8d8;font-size:.85rem">궁합 점수</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div style="background:#1a1040;border:2px solid #7ec8e3;border-radius:14px;
          padding:20px;text-align:center">
          <div style="color:#7ec8e3;font-size:1.2rem;font-weight:700">{result['관계']}</div>
          <div style="color:#a8b8d8;font-size:.85rem;margin-top:4px">오행 관계</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#1a1040;border:2px solid #4caf50;border-radius:14px;
          padding:20px;text-align:center">
          <div style="color:#4caf50;font-size:1.1rem;font-weight:700">
            {result['A오행']} × {result['B오행']}
          </div>
          <div style="color:#a8b8d8;font-size:.85rem;margin-top:4px">주요 오행</div>
        </div>""", unsafe_allow_html=True)

    st.info(result["설명"])

    # ── 오행 비교 ─────────────────────────────────────
    st.markdown("---")
    st.subheader("🌈 두 사람 오행 비교")
    for oh in ["목","화","토","금","수"]:
        m = OHAENG_META[oh]
        c1,c2,c3 = st.columns([1,2,2])
        with c1: st.markdown(f"**{m['emoji']} {oh}**")
        with c2: st.progress(vec1.get(oh,0), text=f"{p1_name}: {int(vec1.get(oh,0)*100)}%")
        with c3: st.progress(vec2.get(oh,0), text=f"{p2_name}: {int(vec2.get(oh,0)*100)}%")

    # ── TOP5 카드 ─────────────────────────────────────
    st.markdown("---")
    st.markdown(f"## 🌍 {p1_name} + {p2_name}이 함께 살기 좋은 지역 TOP 5")

    MEDALS = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    RANK_COLOR = ["#e2c27d","#c0c0c0","#cd7f32","#a8b8d8","#a8b8d8"]

    for i, r in enumerate(top5):
        with st.expander(
            f"{MEDALS[i]}  **{r['region']}**, {r['country']}  —  궁합 유사도 {r['score']}%",
            expanded=(i == 0)
        ):
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"*{r['설명']}*")
                trait_html = " ".join([
                    f'<span style="background:#1a2a3a;border-radius:20px;padding:3px 10px;'
                    f'color:#7ec8e3;font-size:.8rem">{t}</span>' for t in r["특성"]])
                st.markdown(f'<div>{trait_html}</div>', unsafe_allow_html=True)
                st.caption(f"🌤 기후: {r['기후']}  |  👥 인구밀도: {r['인구밀도']}  |  🌿 자연도: {int(r['자연도']*100)}%")
            with col2:
                st.markdown(f"""
                <div style="background:#0d1a2a;border:2px solid {RANK_COLOR[i]};border-radius:12px;
                  padding:14px;text-align:center">
                  <div style="color:{RANK_COLOR[i]};font-size:2rem;font-weight:900">{r['score']}%</div>
                  <div style="color:#a8b8d8;font-size:.75rem">궁합 유사도</div>
                </div>""", unsafe_allow_html=True)

    # ── 지도 ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("📍 궁합 지역 지도")
    m = folium.Map(location=[top5[0]["lat"],top5[0]["lng"]],
                   zoom_start=2, tiles="CartoDB dark_matter")
    ICON_COLORS = ["red","blue","green","purple","orange"]
    for i, r in enumerate(top5):
        folium.Marker(
            [r["lat"],r["lng"]],
            popup=folium.Popup(
                f"<b>{MEDALS[i]} {r['region']}</b><br>{r['country']}<br>궁합 {r['score']}%",
                max_width=200),
            tooltip=f"{MEDALS[i]} {r['region']}",
            icon=folium.Icon(color=ICON_COLORS[i], icon="heart", prefix="fa")
        ).add_to(m)
    st_folium(m, width=None, height=460, returned_objects=[])

    # ── 다시하기 ─────────────────────────────────────
    st.markdown("---")
    if st.button("🔄 궁합 다시 보기", use_container_width=True):
        for k in [k for k in st.session_state if k.startswith(("compat","p1","p2"))]:
            st.session_state.pop(k, None)
        st.rerun()
