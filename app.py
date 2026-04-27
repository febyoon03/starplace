"""
StarPlace 🌟  ·  사주·자미두수 기반 나에게 맞는 지역 추천
학번: 2024510007  |  이름: 이윤경
"""
import streamlit as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from db.database import register, login, init_db
init_db()

st.set_page_config(page_title="StarPlace 🌟", page_icon="🌍", layout="centered")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif;}
.hero{background:linear-gradient(135deg,#0d0d1a 0%,#1a1040 50%,#0d2137 100%);
  border-radius:20px;padding:44px 32px;text-align:center;margin-bottom:24px;
  box-shadow:0 8px 40px rgba(0,0,0,.5);}
.hero h1{color:#e2c27d;font-size:2.6rem;margin:0;letter-spacing:2px;}
.hero p{color:#a8b8d8;font-size:1rem;margin-top:8px;}
.badge{display:inline-block;background:rgba(226,194,125,.15);border:1px solid #e2c27d;
  border-radius:20px;padding:5px 16px;color:#e2c27d;font-size:.82rem;margin:4px;}
</style>""", unsafe_allow_html=True)

# ── 첫 화면: 학번 / 이름 항상 표시 ──────────────────────
st.markdown("""
<div class="hero">
  <h1>🌟 StarPlace</h1>
  <p>사주 · 자미두수 · 성향 분석으로 찾는 나에게 맞는 지역</p><br>
  <span class="badge">📚 학번: 2024510007</span>
  <span class="badge">👤 이름: 이윤경</span>
  <span class="badge">🏫 광운대학교 정보융합학과</span>
</div>
""", unsafe_allow_html=True)

# ── 세션 초기화 ──────────────────────────────────────────
for k,v in [("logged_in",False),("user",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ── 로그인 / 회원가입 ────────────────────────────────────
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 로그인", "✨ 회원가입"])

    with tab1:
        uid = st.text_input("아이디", placeholder="아이디 입력", key="l_id")
        upw = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력", key="l_pw")
        if st.button("🚀 로그인", use_container_width=True, type="primary"):
            if not uid or not upw:
                st.error("아이디와 비밀번호를 입력해주세요.")
            else:
                user = login(uid, upw)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success(f"환영해요, {user['nickname']}님! 🌟")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")


    with tab2:
        r_id  = st.text_input("아이디", placeholder="영문+숫자", key="r_id")
        r_pw  = st.text_input("비밀번호", type="password", placeholder="6자 이상", key="r_pw")
        r_pw2 = st.text_input("비밀번호 확인", type="password", key="r_pw2")
        r_nick= st.text_input("닉네임 (선택)", placeholder="표시될 이름", key="r_nick")
        if st.button("🌟 가입하기", use_container_width=True, type="primary"):
            if not r_id or not r_pw:
                st.error("필수 항목을 입력해주세요.")
            elif len(r_pw) < 6:
                st.error("비밀번호는 6자 이상이어야 합니다.")
            elif r_pw != r_pw2:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                ok, msg = register(r_id, r_pw, r_nick)
                if ok:
                    st.success("가입 완료! 로그인 탭에서 로그인해주세요 🎉")
                else:
                    st.error(msg)

    st.markdown("---")
    st.markdown("""
### 🌍 StarPlace란?
생년월일시 기반 **사주팔자** + **자미두수 명궁** + **성향 테스트 10문항**을 종합해  
전 세계 **80개 도시** 중 나에게 가장 잘 맞는 곳을 찾아드립니다.

| 🔮 사주 분석 | 🌟 자미두수 | 🎯 성향 테스트 | 💑 지역 궁합 |
|:-----------:|:----------:|:------------:|:----------:|
| 오행 비율 계산 | 명궁 주성 분석 | 10문항 성향 | 두 사람 공동 최적 지역 |
    """)

else:
    user = st.session_state.user
    st.success(f"🌟 {user['nickname']}님, 환영합니다! 사이드바 메뉴를 이용하세요.")
    col1, col2 = st.columns(2)
    with col1:
        st.info("🗺️ **내 지역 추천** — 왼쪽 메뉴 클릭")
    with col2:
        st.info("💑 **지역 궁합** — 왼쪽 메뉴 클릭")
    if st.button("🚪 로그아웃"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
