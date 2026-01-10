from flask import Flask, request, render_template_string
from openai import OpenAI
import requests
import re
import random
from markupsafe import Markup


app = Flask(__name__)
client = OpenAI()  


#お土産Wikipedia画像表示
def get_wikipedia_image(title):
    url = "https://ja.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "pageimages",
        "pithumbsize": 300,
        "redirects": 1
    }

    headers = {
        "User-Agent": "zemiapp/1.0 (https://example.com)"
    }

    res = requests.get(url, params=params, headers=headers)

    if res.status_code != 200:
        return None

    data = res.json()

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "thumbnail" in page:
            return page["thumbnail"]["source"]

    return None


#旅行プランのWikipedia記述
WIKI_ENDPOINT = "https://ja.wikipedia.org/w/api.php"

def wiki_search_titles(query: str, limit: int = 10):
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
    titles = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        title = re.sub(r"<.*?>", "", title)
        if title:
            titles.append(title)
    return titles

def build_trip(destination: str, days: int, style: str):
    candidates = []
    for q in [f"{destination} 観光", f"{destination} 名所", f"{destination} 寺", f"{destination} 神社"]:
        candidates += wiki_search_titles(q, limit=10)

    # 重複除去
    seen = set()
    pool = []
    for t in candidates:
        if t not in seen:
            seen.add(t)
            pool.append(t)

    if len(pool) < days * 5:
        pool += [
            f"{destination}中心街散策",
            f"{destination}の寺社エリア",
            f"{destination}の景色スポット",
            f"{destination}の商店街・市場",
            f"{destination}の文化施設",
            f"{destination}の自然スポット",
        ]

    if "食べ歩き" in style:
        tips_base = "食べ歩きがしやすいエリアを中心に。混む時間をずらすと◎"
    elif "写真映え" in style:
        tips_base = "光が綺麗な夕方を意識。たくさんの場所を回れるように移動時間は少なめに。"
    elif "ゆったり" in style:
        tips_base = "移動少なめ。カフェ休憩を挟んでゆったり回る。"
    else:
        tips_base = "王道スポットは朝に。午後は近場でまとめると効率的。"

    time_slots = ["09:00", "11:00", "12:30", "15:00", "18:00"]
    labels = ["朝", "午前", "昼", "午後", "夜"]

    random.shuffle(pool)
    need = days * len(time_slots)
    picks = pool[:need] if len(pool) >= need else (pool * ((need // len(pool)) + 1))[:need]

    plan = []
    idx = 0
    for d in range(1, days + 1):
        schedule = []
        for i, t in enumerate(time_slots):
            title = picks[idx]
            idx += 1
            if labels[i] == "昼":
                detail = "近くで休憩・ランチを想定。無理のない移動距離で。"
            else:
                detail = "同じエリア内で無理なく巡るプランです。"
            schedule.append({
                "time": t,
                "title": title,
                "detail": detail,
                "tips": tips_base
            })
        plan.append({"day": d, "schedule": schedule})
    return plan


#お土産検索のhtmlを記載
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>AIお土産検索</title>

<style>
body {
  margin: 0;
  padding: 24px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  background: #fbf7ed;
  color: #24324a;
}

.container {
  max-width: 720px;
  margin: 0 auto;
}

h1 {
  font-family: Georgia, serif;
  font-size: 2rem;
  margin-bottom: 8px;
  text-align: center;
}

p.sub {
  color: #6b7a8c;
  margin-bottom: 24px;
  text-align: center;
}

.section {
  margin-bottom: 28px;
}

.section h3 {
  font-size: 1rem;
  margin-bottom: 8px;
}

ul.option-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #e3e7ee;
}

ul.option-list li {
  padding: 14px 16px;
  background: #fff;
  border-bottom: 1px solid #e3e7ee;
  cursor: pointer;
}

ul.option-list li:last-child {
  border-bottom: none;
}

ul.option-list li.active {
  background: #afb3b6;
  color: #fff;
}

.accordion-toggle {
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #e3e7ee;
  background: #eef3f8;
  font-weight: bold;
  cursor: pointer;
}

.accordion-content {
  display: none;
  margin-top: 12px;
}

.note {
  font-size: 0.8rem;
  color: #6b7a8c;
  margin-top: 6px;
}

#searchBtn {
  width: 100%;
  padding: 16px;
  font-size: 1rem;
  background: linear-gradient(180deg, #f07a3a, #e45f2b);
  color: #fff;
  border: none;
  border-radius: 14px;
  cursor: pointer;
}

#searchBtn:hover {
  opacity: 0.9;
}

.accordion-toggle {
  width: 100%;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #dfeef6;
  background: #dfeef6;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}

.select-trigger {
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #e3e7ee;
  background: #fff;

  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1rem;
}

.arrow {
  width: 8px;
  height: 8px;
  border-right: 2px solid #e45f2b;
  border-bottom: 2px solid #e45f2b;
  transform: rotate(45deg);
  transition: transform 0.2s ease;
  margin-left: 8px;
}

.select-list {
  margin-top: 10px;
  border-radius: 18px;
  border: 1px solid #e3e7ee;
  background: #fff;
  box-shadow: 0 8px 20px rgba(0,0,0,0.08);
}

.select-trigger span {
  display: inline-block;
}

.select-box {
  margin-bottom: 28px;
}

.select-list {
  list-style: none;
  padding: 0;
  margin-top: 8px;
  border-radius: 14px;
  overflow-y: auto;     
  max-height: 260px;     
  border: 1px solid #e3e7ee;
  background: #fff;
  display: none;
}

.select-list li {
  padding: 14px 16px;
  border-bottom: 1px solid #e3e7ee;
  cursor: pointer;
}

.select-list li:last-child {
  border-bottom: none;
}

.select-list li:hover {
  background: #eef3f8;
}

.accordion-content.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.error-text {
  color: #d9534f;
  font-size: 0.8rem;
  margin-top: 6px;
}

.select-box.error .select-trigger {
  border-color: #d9534f;
}

.result-card {
  background: #dfeef6;  
  border-radius: 20px;
  padding: 20px;
  margin-bottom: 20px;
}

#loading .dot {
  display: inline-block;
  font-weight: bold;
  font-size: 1rem;
  animation: blink 1.4s infinite both;
}

#loading .dot:nth-child(2) { animation-delay: 0.2s; }
#loading .dot:nth-child(3) { animation-delay: 0.4s; }
#loading .dot:nth-child(4) { animation-delay: 0.6s; }

@keyframes blink {
  0%, 20%, 50%, 80%, 100% { opacity: 0; }
  40% { opacity: 1; }
  60% { opacity: 1; }
}

.tripBtn {
  width: 100%;
  padding: 16px;
  font-size: 1rem;
  background: linear-gradient(180deg, #f07a3a, #e45f2b);
  color: #fff;
  border: none;
  border-radius: 14px;
  cursor: pointer;
}

.tripBtn:hover {
  opacity: 0.9;
}

</style>
</head>

<body>
<div class="container">

{{ trip_block }}

<h1>おすすめお土産</h1>
<p class="sub">条件を選ぶとAIがおすすめのお土産を提案します</p>


<form method="post">

      <input type="hidden" name="place" id="place">
      <input type="hidden" name="target" id="target">
      <input type="hidden" name="budget" id="budget">

      <input type="hidden" name="genre" id="genre">
      <input type="hidden" name="shelf" id="shelf">
      <input type="hidden" name="package" id="package">
      <input type="hidden" name="allergy" id="allergy">


  <!-- 旅行先 -->
  <div class="select-box" data-key="place">
    <button type="button" class="select-trigger">
      <span class="label">旅行先</span>
      <span class="value">{{ form.place or "未選択" }}</span>
      <span class="arrow"></span>
    </button>

    <ul class="select-list">
      <li>北海道</li>
      <li>青森県</li>
      <li>岩手県</li>
      <li>宮城県</li>
      <li>秋田県</li>
      <li>山形県</li>
      <li>福島県</li>
      <li>茨城県</li>
      <li>栃木県</li>
      <li>群馬県</li>
      <li>埼玉県</li>
      <li>千葉県</li>
      <li>東京都</li>
      <li>神奈川県</li>
      <li>新潟県</li>
      <li>富山県</li>
      <li>石川県</li>
      <li>福井県</li>
      <li>山梨県</li>
      <li>長野県</li>
      <li>岐阜県</li>
      <li>静岡県</li>
      <li>愛知県</li>
      <li>三重県</li>
      <li>滋賀県</li>
      <li>京都府</li>
      <li>大阪府</li>
      <li>兵庫県</li>
      <li>奈良県</li>
      <li>和歌山県</li>
      <li>鳥取県</li>
      <li>島根県</li>
      <li>岡山県</li>
      <li>広島県</li>
      <li>山口県</li>
      <li>徳島県</li>
      <li>香川県</li>
      <li>愛媛県</li>
      <li>高知県</li>
      <li>福岡県</li>
      <li>佐賀県</li>
      <li>長崎県</li>
      <li>熊本県</li>
      <li>大分県</li>
      <li>宮崎県</li>
      <li>鹿児島県</li>
      <li>沖縄県</li>
    </ul>
  </div>

  <!-- 渡す相手 -->
  <div class="select-box" data-key="target">
    <button type="button" class="select-trigger">
      <span class="label">渡す人</span>
      <span class="value">{{ form.target or "未選択" }}</span>
      <span class="arrow"></span>
    </button>

    <ul class="select-list">
      <li>家族</li>
      <li>友人</li>
      <li>恋人</li>
      <li>職場の人</li>
      <li>自分用</li>
    </ul>
  </div>

  <!-- 予算 -->
  <div class="select-box" data-key="budget">
    <button type="button" class="select-trigger">
      <span class="label">予算</span>
      <span class="value">{{ form.budget or "未選択" }}</span>
      <span class="arrow"></span>
    </button>

    <ul class="select-list">
      <li>〜1000円</li>
      <li>〜2000円</li>
      <li>〜3000円</li>
      <li>5000円以上</li>
    </ul>
  </div>

  <!-- ジャンル -->
  <div class="select-box" data-key="genre">
    <button type="button" class="select-trigger">
      <span class="label">カテゴリ</span>
      <span class="value">{{ form.genre or "未選択" }}</span>
      <span class="arrow"></span>
    </button>

    <ul class="select-list">
      <li>お菓子</li>
      <li>和菓子</li>
      <li>洋菓子</li>
      <li>食品</li>
      <li>飲み物</li>
      <li>雑貨</li>
      <li>伝統工芸</li>
      <li>どれでもOK</li>
    </ul>
  </div>

  <!-- こだわり条件 -->
  <div class="section">
    <button type="button" class="accordion-toggle">こだわり条件</button>

    <div class="accordion-content" id="foodOptions">
      <div class="section">
        <h3>日持ち</h3>
        <ul class="option-list" data-key="shelf">
          <li>気にしない</li>
          <li>7日以上</li>
          <li>14日以上</li>
        </ul>
      </div>

      <div class="section">
        <h3>個包装</h3>
        <ul class="option-list" data-key="package">
          <li>どちらでも</li>
          <li>個包装がいい</li>
        </ul>
      </div>

      <div class="section">
        <h3>アレルギー</h3>
        <ul class="option-list" data-key="allergy">
          <li>気にしない</li>
          <li>配慮したい</li>
        </ul>
      </div>
    </div>
  </div>

  <button id="searchBtn" type="submit">AIに探してもらう</button>
</form>

<!--AI考え中アニメーション-->
<div id="loading" style="display:none; text-align:center; margin:20px 0;">
  <span class="dot">AI考え中</span><span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
</div>

{% if souvenirs %}
<hr style="margin:40px 0; border:none; border-top:1px solid #ddd;">

<h2>おすすめお土産</h2>

<div class="results">
  {% for s in souvenirs %}
    <div class="result-card">

      <h3>{{ s.name }}</h3>

      {% if s.image %}
        <img src="{{ s.image }}" alt="{{ s.name }}" style="
          width:100%;
          max-width:300px;
          border-radius:12px;
          margin-bottom:8px;
        ">
      {% endif %}

      <p>{{ s.description }}</p>
    </div>
  {% endfor %}
</div>
{% endif %}
</div>

<script>
const state = {};

// option-list（こだわり条件用）
document.querySelectorAll(".option-list").forEach(list => {
  const key = list.dataset.key;
  list.querySelectorAll("li").forEach(item => {
    item.addEventListener("click", () => {
      list.querySelectorAll("li").forEach(li => li.classList.remove("active"));
      item.classList.add("active");
      state[key] = item.textContent;
      console.log(state);
    });
  });
});

// accordion
const toggle = document.querySelector(".accordion-toggle");
const content = document.querySelector(".accordion-content");

toggle.addEventListener("click", () => {
  content.style.display = content.style.display === "block" ? "none" : "block";
});

// select-box（旅行先・渡す人・予算・ジャンル共通）
document.querySelectorAll(".select-box").forEach(box => {
  const key = box.dataset.key;
  const trigger = box.querySelector(".select-trigger");
  const list = box.querySelector(".select-list");
  const value = box.querySelector(".value");

  trigger.addEventListener("click", () => {
    list.style.display = list.style.display === "block" ? "none" : "block";
  });

  list.querySelectorAll("li").forEach(li => {
    li.addEventListener("click", () => {
      value.textContent = li.textContent;
      list.style.display = "none";
      state[key] = li.textContent;
      console.log(state);

      if (key === "genre") {
        const foodGenres = ["お菓子", "和菓子", "洋菓子", "食品", "飲み物"];
        if (foodGenres.includes(li.textContent)) {
          content.classList.remove("disabled");
        } else {
          content.classList.add("disabled");
          ["shelf", "package", "allergy"].forEach(k => {
            state[k] = "";
            document
              .querySelectorAll(`.option-list[data-key="${k}"] li`)
              .forEach(li => li.classList.remove("active"));
          });
        }
      }
    });
  });
});

const form = document.querySelector('input[name="place"]').closest("form");
const hiddenInputs = {
  place: form.querySelector('input[name="place"]'),
  target: form.querySelector('input[name="target"]'),
  budget: form.querySelector('input[name="budget"]'),
  genre: form.querySelector('input[name="genre"]'),
  shelf: form.querySelector('input[name="shelf"]'),
  package: form.querySelector('input[name="package"]'),
  allergy: form.querySelector('input[name="allergy"]'),
};

form.addEventListener("submit", (e) => {
  let hasError = false;

  const requiredKeys = ["place", "target", "budget", "genre"];

  requiredKeys.forEach(key => {
    const box = document.querySelector(`.select-box[data-key="${key}"]`);
    const displayValue = box.querySelector(".value").textContent;

    box.classList.remove("error");
    const oldError = box.querySelector(".error-text");
    if (oldError) oldError.remove();

    if (displayValue === "未選択") {
      hasError = true;
      box.classList.add("error");

      const error = document.createElement("div");
      error.className = "error-text";
      error.textContent = "選択してください";
      box.appendChild(error);
    }
  });

  if (hasError) {
    e.preventDefault();
    return;
  }

  Object.keys(hiddenInputs).forEach(key => {
    const box = document.querySelector(`.select-box[data-key="${key}"]`);
    if (box) {
      hiddenInputs[key].value =
        box.querySelector(".value").textContent !== "未選択"
          ? box.querySelector(".value").textContent
          : "";
    } else {
      hiddenInputs[key].value = state[key] || "";
    }
  });

  document.getElementById("loading").style.display = "block";
});
</script>

</body>
</html>
"""

TRIP_BLOCK = r"""
<h1>旅行プラン生成</h1>
<p class="sub">AIが旅行プランを作成します</p>

<form method="post">
  <div class="section">
    <h3>行き先</h3>
    <input name="destination" value="{{ destination or '京都' }}" style="width:100%;padding:14px 16px;border-radius:14px;border:1px solid #e3e7ee;">
  </div>

  <div class="section">
    <h3>日数（1〜7）</h3>
    <input type="number" name="days" min="1" max="7" value="{{ days or 3 }}" style="width:100%;padding:14px 16px;border-radius:14px;border:1px solid #e3e7ee;">
  </div>

  <div class="section">
    <h3>旅の雰囲気</h3>
    <select name="style" style="width:100%;padding:14px 16px;border-radius:14px;border:1px solid #e3e7ee;background:#fff;">
      {% set s = style or "王道観光" %}
      <option {{ "selected" if s=="王道観光" else "" }}>王道観光</option>
      <option {{ "selected" if s=="ゆったり" else "" }}>ゆったり</option>
      <option {{ "selected" if s=="食べ歩き多め" else "" }}>食べ歩き多め</option>
      <option {{ "selected" if s=="写真映え" else "" }}>写真映え</option>
      <option {{ "selected" if s=="落ち着いた旅" else "" }}>落ち着いた旅</option>
    </select>
  </div>

  <button class="tripBtn" id="tripBtn" type="submit">旅行プランを作成する</button>

</form>

{% if trip %}
<hr style="margin:40px 0; border:none; border-top:1px solid #ddd;">
<h2 style="text-align:center;">{{ destination }} {{ days }}日プラン</h2>

{% for d in trip %}
  <div class="result-card">
    <h3>Day {{ d.day }}</h3>
    {% for s in d.schedule %}
      <p style="margin:12px 0;">
        <b>{{ s.time }}</b> {{ s.title }}<br>
        {{ s.detail }}<br>
        <span style="color:#6b7a8c; font-size:0.9rem;">Tips: {{ s.tips }}</span>
      </p>
    {% endfor %}
  </div>
{% endfor %}
{% endif %}

<hr style="margin:40px 0; border:none; border-top:1px solid #ddd;">
"""
@app.route("/", methods=["GET", "POST"])
def index():
    trip = None
    destination = None
    days = 3
    style = "王道観光"
    souvenirs = []

    if request.method == "POST":
        if request.form.get("destination"):
            destination = request.form.get("destination")
            days = int(request.form.get("days", 3))
            style = request.form.get("style", "王道観光")
            trip = build_trip(destination, days, style)
        else:
            place = request.form.get("place")
            target = request.form.get("target")
            budget = request.form.get("budget")
            genre = request.form.get("genre")
            shelf = request.form.get("shelf")
            package = request.form.get("package")
            allergy = request.form.get("allergy")

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

    return render_template_string(
        INDEX_HTML,
        trip_block=Markup(
            render_template_string(
                TRIP_BLOCK,
                trip=trip,
                destination=destination,
                days=days,
                style=style
            )
        ),
        souvenirs=souvenirs,
        form=request.form,
        destination=destination,
        days=days,
        style=style
    )

    return render_template_string(
        INDEX_HTML,
        trip_block=Markup(
            render_template_string(
                TRIP_BLOCK,
                trip=trip,
                destination=destination,
                days=days,
                style=style
            )
        ),
        souvenirs=souvenirs,
        form=request.form,
        destination=destination,
        days=days,
        style=style
    )




if __name__ == "__main__":
    app.run(debug=True)
