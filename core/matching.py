"""지역 매칭 — 오행 벡터 코사인 유사도"""
import json, math
import streamlit as st

@st.cache_data
def load_regions() -> list:
    """지역 DB 로드 (캐싱 — JSON 파일 반복 I/O 방지)"""
    with open("data/regions.json", "r", encoding="utf-8") as f:
        return json.load(f)

def _cos_sim(a: dict, b: dict) -> float:
    keys = ["목","화","토","금","수"]
    va = [a.get(k,0) for k in keys]
    vb = [b.get(k,0) for k in keys]
    dot = sum(x*y for x,y in zip(va,vb))
    ma = math.sqrt(sum(x**2 for x in va))
    mb = math.sqrt(sum(x**2 for x in vb))
    return dot/(ma*mb) if ma and mb else 0.0

def merge_vectors(saju_vec:dict, quiz_vec:dict, ziwei_vec:dict,
                  w=(0.45, 0.35, 0.20)) -> dict:
    """사주(45%) + 퀴즈(35%) + 자미두수(20%) 가중 합산"""
    keys = ["목","화","토","금","수"]
    merged = {k: w[0]*saju_vec.get(k,0)+w[1]*quiz_vec.get(k,0)+w[2]*ziwei_vec.get(k,0) for k in keys}
    total = sum(merged.values()) or 1
    return {k: round(v/total,3) for k,v in merged.items()}

def get_top5(user_vec: dict, regions: list) -> list:
    scored = sorted(regions, key=lambda r: _cos_sim(user_vec, r["오행"]), reverse=True)
    return [{**r, "score": round(_cos_sim(user_vec, r["오행"])*100, 1)} for r in scored[:5]]

SANGSAENG = {"목":"화","화":"토","토":"금","금":"수","수":"목"}
SANGGEUK  = {"목":"토","토":"수","수":"화","화":"금","금":"목"}

def get_compatibility(vec_a:dict, vec_b:dict, regions:list) -> dict:
    keys = ["목","화","토","금","수"]
    avg = {k: round((vec_a.get(k,0)+vec_b.get(k,0))/2,3) for k in keys}
    places = get_top5(avg, regions)
    ma = max(vec_a, key=vec_a.get)
    mb = max(vec_b, key=vec_b.get)
    if SANGSAENG.get(ma)==mb or SANGSAENG.get(mb)==ma:
        rel, score, desc = "상생(相生) ✨", 92, f"{ma}와 {mb}는 서로를 키워주는 조화로운 관계예요!"
    elif SANGGEUK.get(ma)==mb or SANGGEUK.get(mb)==ma:
        rel, score, desc = "상극(相剋) ⚡", 76, f"{ma}와 {mb}는 서로 자극하며 성장시키는 역동적 관계예요!"
    elif ma==mb:
        rel, score, desc = "비화(比和) 🤝", 85, f"둘 다 {ma} 기운이 강해 서로를 깊이 이해하는 동질 관계예요!"
    else:
        rel, score, desc = "중화(中和) 🌈", 80, "다른 기운이 균형 있게 어우러지는 보완적 관계예요!"
    return {"top5": places, "avg_vec": avg,
            "관계": rel, "점수": score, "설명": desc, "A오행": ma, "B오행": mb}
