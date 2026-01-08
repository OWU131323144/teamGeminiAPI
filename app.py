import json
import re
import random
import requests
import streamlit as st
from openai import OpenAI

# =========================
# Wikipedia API（共通）
# =========================
WIKI_ENDPOINT = "https://ja.wikipedia.org/w/api.php"

def get_wikipedia_image(title):
    url = WIKI_ENDPOINT
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "pageimages",
        "pithumbsize": 300,
        "redirects": 1
    }
    headers = {"User-Agent": "zemiapp/1.0 (https://example.com)"}
    res = requests.get(url, params=params, headers=headers)
    if res.status_code != 200:
        return None
    data = res.json()
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "thumbnail" in page:
            return page["thumbnail"]["source"]
    return None

def wiki_search(query: str, limit: int = 10):
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": str(limit),
    }
    headers = {
        "User-Agent": "TripPlannerApp/1.0 (edu; contact: student@example.com)",
        "Accept-Language": "ja,en;q=0.8",
    }
    r = requests.get(WIKI_ENDPOINT, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        snippet = re.sub(r"<.*?>", "", snippet)
        results.append({"title": title, "snippet": snippet})
    return results

def safe_wiki_collect(destination: str):
    queries = [
        f"{destination} 観光",
        f"{destination} 観光スポット",
        f"{destination} 名所",
        f"{destination} 歴史",
        f"{destination} 文化",
    ]
    spots = []
    seen = set()
    try:
        for q in queries:
            for item in wiki_search(q, limit=10):
                title = item.get("title", "").strip()
                if not title:
                    continue
                if title in seen:
                    continue
                seen.add(title)
                spots.append(item)
        return spots
    except Exception:
        return []

def style_templates(style: str):
    if "王道" in style:
        theme_pool = ["定番名所めぐり", "歴史と文化", "外せないスポット中心"]
        tip_pool = ["朝早めが混雑回避", "徒歩+公共交通で効率UP", "有名どころは先に回る"]
        lunch_pool = ["名物ランチ", "人気の定番ごはん", "駅近で食事"]
    elif "ゆったり" in style:
        theme_pool = ["のんびり散策", "癒しと自然", "カフェ休憩多め"]
        tip_pool = ["移動は少なめに", "ベンチ/休憩スポットを確保", "時間に余裕を持つ"]
        lunch_pool = ["静かな定食屋", "カフェごはん", "軽めランチ"]
    elif "食べ歩き" in style:
        theme_pool = ["食べ歩き中心", "市場・商店街", "グルメ多め"]
        tip_pool = ["小腹用に小銭/IC", "混む時間をずらす", "食べすぎ注意でシェア◎"]
        lunch_pool = ["市場で食べ比べ", "麺・丼の名物", "屋台系ごはん"]
    elif "写真映え" in style:
        theme_pool = ["写真映えスポット", "景色と街並み", "ライトアップ狙い"]
        tip_pool = ["午前の光が綺麗", "夕方のマジックアワー", "混雑前に撮影優先"]
        lunch_pool = ["映えるカフェ", "見た目かわいいスイーツ", "テラス席"]
    else:
        theme_pool = ["落ち着いた旅", "静かな寺社と街歩き", "大人の観光"]
        tip_pool = ["騒がしい場所は短時間", "予約できる店を選ぶ", "夜は早めに戻る"]
        lunch_pool = ["和食中心", "少し贅沢ランチ", "落ち着いた店"]

    return theme_pool, tip_pool, lunch_pool

def build_rule_plan(destination: str, days: int, style: str):
    wiki_spots = safe_wiki_collect(destination)

    titles = [w["title"] for w in wiki_spots if w.get("title")]
    fallback_titles = [
        f"{destination}の代表的な寺社エリア",
        f"{destination}の有名な景色スポット",
        f"{destination}の中心街散策",
        f"{destination}の博物館・文化施設",
        f"{destination}のローカル商店街",
        f"{destination}の公園・自然スポット",
        f"{destination}の夜景・ライトアップ",
        f"{destination}の名物グルメエリア",
    ]

    pool = titles[:] if titles else []
    for t in fallback_titles:
        if t not in pool:
            pool.append(t)

    theme_pool, tip_pool, lunch_pool = style_templates(style)

    time_slots = ["09:00", "11:00", "12:30", "15:00", "18:00"]
    slot_labels = ["朝", "午前", "昼", "午後", "夜"]

    needed = days * len(time_slots)
    random.shuffle(pool)
    picks = pool[:needed] if len(pool) >= needed else (pool * ((needed // len(pool)) + 1))[:needed]

    plan_days = []
    idx = 0

    for d in range(1, days + 1):
        day_theme = random.choice(theme_pool)

        schedule = []
        for s_i, t in enumerate(time_slots):
            spot_title = picks[idx]
            idx += 1

            detail = ""
            if slot_labels[s_i] == "朝":
                detail = "朝は混雑しにくいので、人気スポットからスタート。周辺も軽く散策。"
            elif slot_labels[s_i] == "午前":
                detail = "同じエリア内で徒歩移動できる場所を組み合わせて、効率よく回る。"
            elif slot_labels[s_i] == "昼":
                detail = f"{random.choice(lunch_pool)}を想定。近くのお店で休憩しながら。"
            elif slot_labels[s_i] == "午後":
                detail = "午後は景色・体験・街歩きなど、ゆとりを持って楽しむ。"
            else:
                detail = "夜は食事と散歩。ライトアップや夜景があれば優先。"

            tips = random.choice(tip_pool)

            schedule.append({
                "time": t,
                "title": spot_title,
                "detail": detail,
                "tips": tips
            })

        plan_days.append({
            "day": d,
            "theme": day_theme,
            "schedule": schedule
        })

    notes = [
        "※このプランはWikipedia検索結果とルールベースで自動生成しています。",
        "※混雑状況により、朝は人気スポット→昼は休憩→午後はゆったり、の順が安定です。",
        "※気になるスポットがあれば、検索して営業時間・休館日を確認してください。"
    ]

    return {
        "title": f"{destination} {days}日プラン（Wikipedia + ルール）",
        "destination": destination,
        "days": plan_days,
        "notes": notes,
        "debug": {"wiki_count": len(wiki_spots)}
    }

# =========================
# お土産提案（OpenAI + Wikipedia画像）
# =========================
client = OpenAI()  # 環境変数 OPENAI_API_KEY を自動で読む

def generate_souvenirs(place, target, budget, genre, shelf, package, allergy):
    prompt = f"""
あなたは日本のお土産に詳しい専門家です。

【条件】
旅行先:{place}
誰向け:{target}
予算:{budget}
ジャンル：{genre}
日持ち：{shelf}
個包装：{package}
アレルギー配慮：{allergy}

【ルール】
条件に合う「日本の伝統的・一般的なお土産」を選び、
**Wikipediaに単独ページがある名称のみ**を使って、
以下の形式で書いてください。
- 「ジャンル」が「食べ物」以外の場合は、日持ち・アレルギー条件は無視してください
- 任意項目が空欄または「気にしない」の場合は考慮しなくて構いません
- 予算内で現実的に購入できるものを選んでください
- 日本の一般的・伝統的なお土産に限定してください
- Wikipediaに単独ページが存在する名称のみを使用してください
- Wikipediaに単独ページが存在するという内容は書かないでください。
- 敬語で書いてください
- 一つのお土産に対して4行以上の文章で書いてください。
- どこで売っているかも書いてください。

【出力形式】
以下の形式で6つ提案してください。

1. お土産名：条件に合っている理由が分かる説明
2. お土産名：条件に合っている理由が分かる説明
3. お土産名：条件に合っている理由が分かる説明
4. お土産名：条件に合っている理由が分かる説明
5. お土産名：条件に合っている理由が分かる説明
6. お土産名：条件に合っている理由が分かる説明
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content
    items = text.split("\n")

    souvenirs = []
    for item in items:
        if "：" in item:
            name, desc = item.split("：", 1)
            clean_name = re.sub(r'^[0-9]+\.\s*', '', name).strip()
            clean_name = clean_name.replace("（", "").replace("）", "")

            image_url = get_wikipedia_image(clean_name)

            souvenirs.append({
                "name": clean_name,
                "description": desc.strip(),
                "image": image_url
            })
    return souvenirs

# =========================
# UI / CSS
# =========================
st.set_page_config(page_title="Planning a Trip", page_icon="🧳", layout="centered")

st.markdown("""
<style>
.stApp { background: #f7f1e3; }
.wrap { max-width: 720px; margin: 0 auto; }
.h1 {
  font-family: ui-serif, Georgia, "Times New Roman", serif;
  font-size: 64px;
  font-weight: 800;
  color: #1f2a44;
  margin: 10px 0 14px 0;
  letter-spacing: 0.2px;
}
.panel {
  background: #ffffff;
  border: 2px solid #2c3553;
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 6px 0 rgba(44,53,83,0.05);
  margin-bottom: 14px;
}
.daybar {
  background: #d86b2b;
  color: white;
  font-weight: 800;
  padding: 10px 14px;
  border-radius: 12px 12px 0 0;
  font-size: 18px;
}
.daycard {
  background: #ffffff;
  border: 2px solid #d86b2b;
  border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.row {
  display: grid;
  grid-template-columns: 70px 1fr;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(0,0,0,0.08);
}
.row:last-child { border-bottom: none; }
.time { font-weight: 800; color: #1f2a44; }
.title { font-weight: 800; color: #1f2a44; margin-bottom: 2px; }
.detail { color: rgba(31,42,68,0.85); font-size: 14px; line-height: 1.4; }
.tips { color: rgba(31,42,68,0.7); font-size: 13px; margin-top: 4px; }
.smallnote { color: rgba(31,42,68,0.75); font-size: 13px; }
.badge {
  display:inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid rgba(31,42,68,0.18);
  font-size: 12px;
  color: rgba(31,42,68,0.78);
  background: rgba(255,255,255,0.65);
}
.scard {
  background: #ffffff;
  border: 2px solid #2c3553;
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 12px;
  box-shadow: 0 6px 0 rgba(44,53,83,0.05);
}
.hr {
  margin: 26px 0;
  border: none;
  border-top: 1px solid rgba(0,0,0,0.12);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="h1">Planning a Trip</div>', unsafe_allow_html=True)

# セッション保存（両方同居）
if "plan" not in st.session_state:
    st.session_state.plan = None
if "souvenirs" not in st.session_state:
    st.session_state.souvenirs = None

# ======================================================
# ① 旅行プラン（ページ上部）
# ======================================================
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("### 旅行プラン", unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])
with c1:
    destination = st.text_input("行き先", value="京都", key="trip_destination")
with c2:
    days = st.number_input("日数", min_value=1, max_value=7, value=3, key="trip_days")

style = st.selectbox(
    "旅の雰囲気",
    ["王道観光（定番）", "ゆったり癒し", "食べ歩き多め", "写真映え優先", "大人っぽく落ち着いた旅"],
    index=0,
    key="trip_style"
)

generate_trip = st.button("プランを作成する", use_container_width=True, key="trip_generate")
st.markdown('</div>', unsafe_allow_html=True)

if generate_trip:
    with st.spinner("Wikipediaで候補を集めて、プランを組み立て中..."):
        st.session_state.plan = build_rule_plan(destination, int(days), style)

plan = st.session_state.plan
if plan:
    st.markdown(
        f"<div class='smallnote'>📍 {plan.get('destination','')} / {days} days "
        f"<span class='badge'>Wikipedia候補: {plan.get('debug',{}).get('wiki_count',0)}</span></div>",
        unsafe_allow_html=True
    )

    for d in plan.get("days", []):
        day_num = d.get("day", "")
        theme = d.get("theme", "")
        st.markdown(
            f"<div class='daybar'>Day {day_num}　<span style='font-weight:700; opacity:.9;'>— {theme}</span></div>",
            unsafe_allow_html=True
        )
        st.markdown("<div class='daycard'>", unsafe_allow_html=True)

        for item in d.get("schedule", []):
            t = item.get("time", "")
            title = item.get("title", "")
            detail = item.get("detail", "")
            tips = item.get("tips", "")

            st.markdown(f"""
            <div class="row">
              <div class="time">{t}</div>
              <div>
                <div class="title">{title}</div>
                <div class="detail">{detail}</div>
                <div class="tips">Tips: {tips}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    notes = plan.get("notes", [])
    if notes:
        st.markdown('<div class="panel"><div style="font-weight:800; color:#1f2a44; margin-bottom:6px;">メモ</div>', unsafe_allow_html=True)
        for n in notes:
            st.markdown(f"• <span class='smallnote'>{n}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# 区切り線
st.markdown("<hr class='hr'>", unsafe_allow_html=True)

# ======================================================
# ② お土産提案（同じページ下部）
# ======================================================
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown("### お土産提案", unsafe_allow_html=True)

place = st.text_input("旅行先", value="京都", key="sou_place")
target = st.text_input("誰向け", value="", key="sou_target")
budget = st.text_input("予算", value="", key="sou_budget")

genre = st.selectbox("ジャンル", ["食べ物", "食べ物以外"], index=0, key="sou_genre")
shelf = st.text_input("日持ち", value="気にしない", key="sou_shelf")
package = st.selectbox("個包装", ["気にしない", "希望する", "不要"], index=0, key="sou_package")
allergy = st.text_input("アレルギー配慮", value="気にしない", key="sou_allergy")

generate_sou = st.button("お土産を提案する", use_container_width=True, key="sou_generate")
st.markdown('</div>', unsafe_allow_html=True)

if generate_sou:
    with st.spinner("お土産を提案中..."):
        st.session_state.souvenirs = generate_souvenirs(
            place=place,
            target=target,
            budget=budget,
            genre=genre,
            shelf=shelf,
            package=package,
            allergy=allergy
        )

souvenirs = st.session_state.souvenirs
if souvenirs:
    for s in souvenirs:
        st.markdown('<div class="scard">', unsafe_allow_html=True)
        c_img, c_txt = st.columns([1, 2])
        with c_img:
            if s.get("image"):
                st.image(s["image"], use_container_width=True)
            else:
                st.write("")
        with c_txt:
            st.markdown(f"**{s.get('name','')}**")
            st.write(s.get("description", ""))
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
