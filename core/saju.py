"""사주팔자(四柱八字) 계산 모듈"""
from korean_lunar_calendar import KoreanLunarCalendar
import streamlit as st

CHEONGAN = ["갑","을","병","정","무","기","경","신","임","계"]
JIJI     = ["자","축","인","묘","진","사","오","미","신","유","술","해"]

CHEONGAN_OHAENG = {
    "갑":"목","을":"목","병":"화","정":"화","무":"토",
    "기":"토","경":"금","신":"금","임":"수","계":"수"
}
JIJI_OHAENG = {
    "자":"수","축":"토","인":"목","묘":"목","진":"토","사":"화",
    "오":"화","미":"토","신":"금","유":"금","술":"토","해":"수"
}

OHAENG_META = {
    "목":{"emoji":"🌿","color":"#4caf50","keyword":"나무·성장·봄","desc":"성장 지향, 창의적, 인내력"},
    "화":{"emoji":"🔥","color":"#f44336","keyword":"불꽃·열정·여름","desc":"열정적, 표현력, 카리스마"},
    "토":{"emoji":"🏔️","color":"#ff9800","keyword":"대지·안정·사계","desc":"안정 추구, 신중함, 포용력"},
    "금":{"emoji":"⚙️","color":"#9e9e9e","keyword":"쇠·결단·가을","desc":"원칙주의, 완벽주의, 결단력"},
    "수":{"emoji":"💧","color":"#2196f3","keyword":"물·지혜·겨울","desc":"지혜, 유연성, 탐구적"},
}

HOUR_JIJI_MAP = [
    (range(23,24), "해"), (range(0,1), "자"), (range(1,3), "축"),
    (range(3,5), "인"), (range(5,7), "묘"), (range(7,9), "진"),
    (range(9,11), "사"), (range(11,13), "오"), (range(13,15), "미"),
    (range(15,17), "신"), (range(17,19), "유"), (range(19,21), "술"),
    (range(21,23), "해"),
]

def _hour_to_jiji(hour: int) -> str:
    for rng, jiji in HOUR_JIJI_MAP:
        if hour in rng:
            return jiji
    return "자"

def _year_ganji(year: int):
    return CHEONGAN[(year-4)%10], JIJI[(year-4)%12]

def _month_ganji(year: int, month: int):
    ji_idx = (month+1) % 12
    base = [2,4,6,8,0,2,4,6,8,0]
    gan_idx = (base[(year-4)%10] + month - 1) % 10
    return CHEONGAN[gan_idx], JIJI[ji_idx]

def _day_ganji(year: int, month: int, day: int):
    cal = KoreanLunarCalendar()
    cal.setSolarDate(year, month, day)
    gapja = cal.getGapJaString()
    parts = gapja.split()
    if len(parts) >= 3:
        d = parts[2].replace("일","")
        if len(d) >= 2 and d[0] in CHEONGAN and d[1] in JIJI:
            return d[0], d[1]
    total = (year-1900)*365 + month*30 + day
    return CHEONGAN[total%10], JIJI[total%12]

def _hour_ganji(day_gan: str, hour: int):
    ji = _hour_to_jiji(hour)
    base = {"갑":0,"을":0,"병":2,"정":2,"무":4,"기":4,"경":6,"신":6,"임":8,"계":8}
    gan_idx = (base.get(day_gan,0) + JIJI.index(ji)) % 10
    return CHEONGAN[gan_idx], ji

@st.cache_data
def calculate_saju(year:int, month:int, day:int, hour:int, gender:str) -> dict:
    """사주팔자 계산 (캐싱 — 동일 입력 반복 계산 방지)"""
    y_gan, y_ji = _year_ganji(year)
    m_gan, m_ji = _month_ganji(year, month)
    d_gan, d_ji = _day_ganji(year, month, day)
    h_gan, h_ji = _hour_ganji(d_gan, hour)

    pillars = [
        {"주":"년주","천간":y_gan,"지지":y_ji},
        {"주":"월주","천간":m_gan,"지지":m_ji},
        {"주":"일주","천간":d_gan,"지지":d_ji},
        {"주":"시주","천간":h_gan,"지지":h_ji},
    ]

    score = {"목":0.0,"화":0.0,"토":0.0,"금":0.0,"수":0.0}
    for p in pillars:
        if p["천간"] in CHEONGAN_OHAENG:
            score[CHEONGAN_OHAENG[p["천간"]]] += 1.0
        if p["지지"] in JIJI_OHAENG:
            score[JIJI_OHAENG[p["지지"]]] += 0.8

    total = sum(score.values()) or 1
    ratio = {k: round(v/total, 3) for k,v in score.items()}
    sorted_oh = sorted(ratio.items(), key=lambda x:x[1], reverse=True)

    return {
        "pillars": pillars,
        "오행비율": ratio,
        "주요오행": sorted_oh[0][0],
        "2위오행": sorted_oh[1][0],
        "일간": d_gan,
        "음양": "양(陽)" if CHEONGAN.index(d_gan)%2==0 else "음(陰)",
        "gender": gender,
    }
