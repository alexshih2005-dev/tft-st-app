import streamlit as st
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from bs4 import BeautifulSoup

# 設定頁面資訊
st.set_page_config(page_title="TFT 戰情觀察室", layout="wide", page_icon="🏆")

# === 玩家清單 ===
PLAYERS = [
    {"name": "MilKer", "url": "https://www.metatft.com/player/tw/MilKer-MK86"},
    {"name": "Godbaby", "url": "https://www.metatft.com/player/tw/Godbaby-6078"},
    {"name": "東川派崔武鎮", "url": "https://www.metatft.com/player/tw/%E6%9D%B1%E5%B7%9D%E6%B4%BE%E5%B4%94%E6%AD%A6%E9%8E%AE-2280"},
    {"name": "LordShao", "url": "https://www.metatft.com/player/tw/LordShao-2549"},
    {"name": "Roku", "url": "https://www.metatft.com/player/tw/Roku-4059"}
]

# === 漢化字典 ===
TRANSLATION_MAP = {
    "Flexible": "陣容靈活", "Economy": "營運高手", "Tank": "坦克愛好", 
    "AD": "偏好物理", "AP": "偏好法術", "Tempo": "高節奏", "Forcer": "鐵頭娃", 
    "Damage": "高傷害", "Pacifist": "和平主義", "Consistent": "表現穩定", 
    "Hot Streak": "手感發燙", "Cold Streak": "手感冰冷", "High Tempo": "快節奏", 
    "Prefers AD": "主打物理", "Prefers AP": "主打法術", "One Trick": "絕活哥", 
    "Late Game": "後期陣容", "Strong Frontline": "前排穩固", "Chain Wins": "連勝中", 
    "Chain Losses": "連敗中", "Good MMR": "隱分高", "Bad MMR": "隱分低", "Passive": "被動",
    "Bilgewater": "比爾吉沃特", "Noxus": "諾克薩斯", "Ionia": "愛歐尼亞",
    "Shadow Isles": "暗影島", "Demacia": "戴瑪西亞", "Shurima": "蘇瑞瑪",
    "Piltover": "皮爾托福", "Zaun": "佐恩", "Freljord": "弗雷爾卓德",
    "Targon": "巨石峰", "Void": "虛空", "Slayer": "殺戮者",
    "Nautilus": "納帝魯斯", "Miss Fortune": "好運姐", "Aphelios": "亞菲利歐",
    "Sion": "賽恩", "Swain": "斯溫", "Azir": "阿祈爾", "Lux": "拉克絲",
    "Ahri": "阿璃", "Kai'Sa": "凱莎", "God": "之神", "Enjoyer": "愛好者", "Main": "專精"
}

def translate_tag(tag):
    if tag in TRANSLATION_MAP: return TRANSLATION_MAP[tag]
    for en, tw in TRANSLATION_MAP.items():
        if en in tag: tag = tag.replace(en, tw)
    if "God" in tag: tag = tag.replace("God", "之神")
    if "Enjoyer" in tag: tag = tag.replace("Enjoyer", "愛好者")
    if "Main" in tag: tag = tag.replace("Main", "專精")
    return tag

def get_rank_score(rank_str, lp_str):
    tiers = {"Challenger": 9000, "Grandmaster": 8000, "Master": 7000, "Diamond": 6000, "Emerald": 5000, "Platinum": 4000, "Gold": 3000, "Silver": 2000, "Bronze": 1000, "Iron": 0}
    score = 0
    for t, val in tiers.items():
        if t in rank_str: score += val; break
    if " I" in rank_str and "V" not in rank_str: score += 300
    elif " II" in rank_str: score += 200
    elif " III" in rank_str: score += 100
    try: score += int(re.sub(r"[^0-9]", "", lp_str))
    except: pass
    return score

# --- 圖表生成器 ---
def generate_grid_2x10(data_points):
    if not data_points: return '<div style="color:#444; font-size:10px;">NO DATA</div>'
    html = '<div class="grid-hist">'
    games = data_points[:20]
    for g in games:
        html += f'<div class="g-box p-{g}">{g}</div>'
    for _ in range(20 - len(games)):
        html += '<div class="g-box empty"></div>'
    html += '</div>'
    return html

def generate_weighted_trend_chart(data_points):
    if not data_points: return ''
    scores_map = {1: 40, 2: 30, 3: 20, 4: 10, 5: -10, 6: -20, 7: -30, 8: -40}
    games_reversed = data_points[:20][::-1] 
    cumulative_score = 0
    trend_points = [0]
    for rank in games_reversed:
        change = scores_map.get(rank, 0)
        cumulative_score += change
        trend_points.append(cumulative_score)
    width = 120; height = 40; padding = 2
    min_score = min(trend_points); max_score = max(trend_points)
    score_range = max_score - min_score if max_score != min_score else 1
    svg_points = []
    step_x = width / (len(trend_points) - 1)
    for i, score in enumerate(trend_points):
        x = i * step_x
        y = ((max_score - score) / score_range) * (height - 2*padding) + padding
        svg_points.append(f"{x},{y}")
    line_color = "#4ade80" if cumulative_score >= 0 else "#ef4444" 
    zero_line = ""
    if min_score < 0 < max_score:
        y_zero = ((max_score - 0) / score_range) * (height - 2*padding) + padding
        zero_line = f'<line x1="0" y1="{y_zero}" x2="{width}" y2="{y_zero}" stroke="#333" stroke-width="1" stroke-dasharray="2" />'
    return f"""<svg viewBox="0 0 {width} {height}" style="width:100%; height:100%; overflow:visible;">{zero_line}<polyline points="{' '.join(svg_points)}" fill="none" stroke="{line_color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" /><circle cx="{svg_points[-1].split(',')[0]}" cy="{svg_points[-1].split(',')[1]}" r="2" fill="{line_color}" /></svg>"""

def generate_bar_chart(data_points):
    if not data_points: return ''
    counts = {i: 0 for i in range(1, 9)}
    for r in data_points: counts[r] += 1
    FIXED_MAX = 8 
    html = '<div class="bar-chart-container">'
    for i in range(1, 9):
        count = counts[i]
        pct = min((count / FIXED_MAX) * 100, 100)
        color = "#3f3f46" 
        if i == 1: color = "#facc15" 
        elif i == 2: color = "#9ca3af"
        elif i == 3: color = "#ca8a04"
        elif i == 4: color = "#4ade80"
        count_txt = str(count) if count > 0 else ""
        bar_style = f"height:{pct}%; background:{color};" if count > 0 else "height:1px; background:#222;"
        html += f"""<div class="bar-col"><div class="bar-top-num">{count_txt}</div><div class="bar-body" style="{bar_style}"></div><div class="bar-btm-lbl">{i}</div></div>"""
    html += '</div>'
    return html

# === Selenium Setup for Streamlit Cloud ===
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # Streamlit Cloud 上的 Chromium 安裝位置通常由 webdriver_manager 自動處理
    # 但指定 ChromeType.CHROMIUM 可以確保相容性
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

@st.cache_data(ttl=600) # 快取 10 分鐘，避免頻繁請求
def get_player_data(player):
    driver = get_driver()
    try:
        driver.get(player['url'])
        time.sleep(3) # 等待載入
        
        # 簡單的滾動
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        full_text = soup.get_text(" ", strip=True)
        header_text = full_text[:6000]

        data = {
            "name": player['name'], "url": player['url'], "avatar": player['name'][0].upper(),
            "rank": "Unranked", "lp": "0 LP", "rank_score": 0,
            "avg_place": 9.9, "top4_rate": 0.0, "win_rate": 0.0, 
            "avg_str": "-", "top4_str": "-", "win_str": "-",
            "recent_games": [], "tags": []
        }

        # 1. Rank
        rank_pattern = re.compile(r"(Challenger|Grandmaster|Master|Diamond|Platinum|Emerald|Gold|Silver|Bronze)\s*(IV|III|II|I)?\s*(\d+)\s*LP")
        match = rank_pattern.search(full_text)
        if match:
            data['rank'] = f"{match.group(1)} {match.group(2) or ''}".strip()
            data['lp'] = f"{match.group(3)} LP"
        else:
            tm = re.search(r"(Challenger|Grandmaster|Master|Diamond|Platinum|Emerald|Gold|Silver)\s*(IV|III|II|I)", full_text)
            if tm: data['rank'] = tm.group(0)
        data['rank_score'] = get_rank_score(data['rank'], data['lp'])

        # 2. Stats
        if "Avg Place" in full_text:
            avg_m = re.search(r"(\d+\.\d+)\s*Avg", full_text)
            if avg_m: 
                data['avg_str'] = avg_m.group(1)
                data['avg_place'] = float(avg_m.group(1))
            top4_m = re.search(r"(\d+\.?\d*)%\s*Top", full_text)
            if top4_m: 
                data['top4_str'] = f"{top4_m.group(1)}%"
                data['top4_rate'] = float(top4_m.group(1))
            win_m = re.search(r"(\d+\.?\d*)%\s*Win", full_text)
            if win_m: 
                data['win_str'] = f"{win_m.group(1)}%"
                data['win_rate'] = float(win_m.group(1))

        # 3. Recent Games
        l20_header = soup.find(string=re.compile("Last 20 Games"))
        if l20_header:
            all_elements = l20_header.find_all_next("div", limit=200)
            history = []
            for el in all_elements:
                txt = el.get_text(strip=True)
                if re.match(r"^[1-8]$", txt) and not el.find_all():
                    history.append(int(txt))
                    if len(history) >= 20: break
            if history: data['recent_games'] = history

        # 4. Tags
        found_tags = []
        dynamic_tags = re.findall(r"([A-Za-z']+\s(?:God|Enjoyer|Main|King))", header_text)
        for t in dynamic_tags:
            if len(t) < 30 and t not in found_tags: found_tags.append(t)
        for tag_en in TRANSLATION_MAP.keys():
            if tag_en in ["AD", "AP", "Tank"]: continue 
            if re.search(r"\b" + re.escape(tag_en) + r"\b", header_text):
                if tag_en not in found_tags: found_tags.append(tag_en)
        final_tags = list(set(found_tags))
        data['tags'] = [translate_tag(t) for t in final_tags]

        return data
    except Exception as e:
        st.error(f"Error fetching {player['name']}: {e}")
        return None
    finally:
        driver.quit()

# === 主介面生成 ===
def main():
    st.title("🏆 TFT 戰情觀察室 V21 (Streamlit 版)")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🔄 刷新數據", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        st.caption(f"最後更新時間: {datetime.datetime.now().strftime('%H:%M:%S')}")

    # 顯示載入動畫
    with st.spinner('正在從 MetaTFT 獲取最新戰績...'):
        results = []
        for p in PLAYERS:
            res = get_player_data(p)
            if res: results.append(res)

    # 計算最佳數據
    valid_avgs = [p['avg_place'] for p in results if p['avg_place'] != 9.9]
    valid_top4 = [p['top4_rate'] for p in results]
    valid_win = [p['win_rate'] for p in results]
    best_avg = min(valid_avgs) if valid_avgs else 0
    best_top4 = max(valid_top4) if valid_top4 else 0
    best_win = max(valid_win) if valid_win else 0

    results.sort(key=lambda x: x['rank_score'], reverse=True)

    # 產生 HTML 表格字串
    html_content = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500;700&family=Noto+Sans+TC:wght@500;700&display=swap');
        body { background: #0e1117; color: #a1a1aa; font-family: 'Noto Sans TC', sans-serif; }
        
        /* 表格結構 */
        .row {
            display: grid;
            grid-template-columns: 40px 200px 150px 180px 240px 140px 180px minmax(300px, 1fr);
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 4px;
            margin-bottom: 8px;
            align-items: center;
            min-height: 90px;
            padding: 10px 0;
            transition: 0.1s;
            column-gap: 15px;
        }
        .row:hover { background: #202023; border-color: #555; }
        
        .col { padding: 0 5px; height: 100%; display: flex; align-items: center; border-right: 1px solid #27272a; }
        .col.center { justify-content: center; text-align: center; }
        .col:last-child { border-right: none; }
        
        .idx { font-weight: bold; font-size: 1.2em; color: #52525b; width: 100%; text-align: center; }
        .rank-1 { border-left: 3px solid #facc15; background: linear-gradient(90deg, rgba(250, 204, 21, 0.05), transparent); }
        .rank-1 .idx { color: #facc15; }

        .player { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 34px; height: 34px; border-radius: 6px; background: #27272a; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #71717a; border: 1px solid #3f3f46; }
        .name { color: #e4e4e7; font-weight: bold; text-decoration: none; font-size: 1.1em; }
        
        .rank-box { display: flex; flex-direction: column; }
        .rank-txt { font-weight: bold; color: #f4f4f5; font-size: 1em; }
        .lp { color: #38bdf8; font-family: 'Roboto Mono'; font-size: 0.9em; }

        .stats { display: flex; gap: 15px; text-align: center; width: 100%; justify-content: center; }
        .stat div:first-child { font-family: 'Roboto Mono'; font-weight: bold; font-size: 1.1em; color: #d4d4d8; }
        .stat div:last-child { font-size: 0.7em; color: #52525b; margin-top: 1px; }
        .best-stat { color: #fff !important; text-shadow: 0 0 8px rgba(255, 255, 255, 0.7); }

        .grid-hist { display: grid; grid-template-columns: repeat(10, 20px); grid-template-rows: repeat(2, 20px); gap: 2px; }
        .g-box { width: 20px; height: 20px; border-radius: 2px; display: flex; align-items: center; justify-content: center; font-family: 'Roboto Mono'; font-weight: bold; font-size: 10px; color: #111; }
        .g-box.empty { background: #222; border: 1px solid #2a2a2a; }
        .p-1 { background: #facc15; } .p-2 { background: #94a3b8; color: #fff; } .p-3 { background: #ca8a04; color: #fff; }
        .p-4 { background: #4ade80; } .p-5, .p-6, .p-7, .p-8 { background: #3f3f46; color: #a1a1aa; }

        .line-container { width: 100%; height: 50px; display: flex; align-items: center; padding: 0 5px; }

        .bar-chart-container { 
            display: flex; width: 100%; height: 60px; align-items: flex-end; gap: 3px; 
            position: relative;
            border-bottom: 1px solid #333;
        }
        .bar-chart-container::before {
            content: ""; position: absolute; left: 0; right: 0; top: 50%; height: 1px; 
            background: rgba(255,255,255,0.05); pointer-events: none;
        }
        .bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; z-index: 1; }
        .bar-top-num { font-family: 'Roboto Mono'; font-size: 10px; color: #e4e4e7; margin-bottom: 2px; font-weight:bold; }
        .bar-body { width: 100%; min-height: 2px; border-radius: 2px 2px 0 0; transition: height 0.3s; }
        .bar-btm-lbl { font-family: 'Roboto Mono'; font-size: 9px; color: #52525b; margin-top: 2px; width: 100%; text-align: center; }

        .tags { display: flex; flex-wrap: wrap; gap: 4px; align-content: center; padding-right: 5px; }
        .tag { font-size: 10px; padding: 3px 6px; background: #27272a; border: 1px solid #3f3f46; border-radius: 3px; color: #a1a1aa; white-space: nowrap; margin-bottom: 2px; }
        .tag.spec { border-color: #facc15; color: #facc15; background: rgba(250, 204, 21, 0.05); }

        .header { 
            display: grid; 
            grid-template-columns: 40px 200px 150px 180px 240px 140px 180px minmax(300px, 1fr); 
            padding: 0 10px; margin-bottom: 5px; font-size: 0.8em; text-transform: uppercase; color: #52525b; column-gap: 15px; 
        }
        .header .center { justify-content: center; display: flex; } 
    </style>

    <div class="header">
        <div class="center">#</div>
        <div>Player</div>
        <div>Rank</div>
        <div class="center">Stats</div>
        <div class="center">Sequence (20)</div>
        <div class="center">Weighted Trend</div>
        <div class="center">Dist (分佈)</div>
        <div>Style</div>
    </div>
    """

    for i, p in enumerate(results):
        rank_cls = "rank-1" if i == 0 else ""
        hl_avg = "best-stat" if p['avg_place'] == best_avg and best_avg != 0 else ""
        hl_top4 = "best-stat" if p['top4_rate'] == best_top4 and best_top4 != 0 else ""
        hl_win = "best-stat" if p['win_rate'] == best_win and best_win != 0 else ""

        grid_html = generate_grid_2x10(p['recent_games'])
        line_html = generate_weighted_trend_chart(p['recent_games'])
        bar_html = generate_bar_chart(p['recent_games'])
        
        tags_html = ""
        for t in p['tags']:
            is_spec = any(k in t for k in ["神", "愛好", "專精", "發燙"])
            cls = "spec" if is_spec else ""
            tags_html += f'<span class="tag {cls}">{t}</span>'

        html_content += f"""
        <div class="row {rank_cls}">
            <div class="col center"><div class="idx">{i+1}</div></div>
            <div class="col">
                <div class="player">
                    <div class="avatar">{p['avatar']}</div>
                    <div class="info">
                        <a href="{p['url']}" target="_blank" class="name">{p['name']}</a>
                        <span style="font-size:10px; color:#555">TW</span>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="rank-box">
                    <span class="rank-txt">{p['rank']}</span>
                    <span class="lp">{p['lp']}</span>
                </div>
            </div>
            <div class="col center">
                <div class="stats">
                    <div class="stat"><div class="{hl_avg}">{p['avg_str']}</div><div>AVG</div></div>
                    <div class="stat"><div class="{hl_top4}">{p['top4_str']}</div><div>TOP4</div></div>
                    <div class="stat"><div class="{hl_win}">{p['win_str']}</div><div>WIN</div></div>
                </div>
            </div>
            <div class="col center">{grid_html}</div>
            <div class="col center"><div class="line-container">{line_html}</div></div>
            <div class="col center">{bar_html}</div>
            <div class="col"><div class="tags">{tags_html}</div></div>
        </div>
        """
    
    st.markdown(html_content, unsafe_allow_html=True)

if __name__ == "__main__":
    main()