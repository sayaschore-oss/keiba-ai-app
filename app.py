import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import google.generativeai as genai
import time
import random

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇", layout="wide")
st.title("🏇 伝説の馬券師AI - 究極解析")
st.caption("netkeibaの出馬表から、最新AIが「期待値のバグ」を炙り出します。")

# --- 設定エリア (Secrets/サイドバー) ---
try:
    # Streamlit CloudのSecretsからキーを取得
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = None

with st.sidebar:
    st.header("⚙️ 設定")
    if not api_key:
        api_key = st.text_input("Google API Keyを入力", type="password")
    else:
        st.success("✅ APIキー適用済み")
    
    model_name = st.selectbox(
        "AIモデル選択", 
        ["models/gemini-3.1-flash-lite", "models/gemini-3.1-pro-preview"],
        help="通常は爆速のflash-lite、勝負レースは熟考のpro-previewがおすすめ。"
    )
    st.divider()
    st.info("スマホでURLをコピーして貼り付けるだけで解析が始まります。")

# --- データ取得エンジン ---
def get_horse_list(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers)
        res.encoding = 'EUC-JP'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        race_name = soup.select_one(".RaceName").get_text(strip=True) if soup.select_one(".RaceName") else "不明なレース"
        race_info = soup.select_one(".RaceData01").get_text(strip=True) if soup.select_one(".RaceData01") else "情報なし"
        
        data = []
        rows = soup.select("tr.HorseList")
        for row in rows:
            target_td = row.select_one("td.HorseInfo")
            if target_td:
                a_tag = target_td.find("a", href=True)
                if a_tag and "/horse/" in a_tag['href']:
                    name = a_tag.text.strip()
                    full_url = "https://db.netkeiba.com" + a_tag['href'] if a_tag['href'].startswith("/") else a_tag['href']
                    data.append({'馬名': name, 'URL': full_url})
        
        return pd.DataFrame(data).drop_duplicates(subset=['馬名']).reset_index(drop=True), race_name, race_info
    except Exception as e:
        st.error(f"出馬表の取得に失敗しました: {e}")
        return pd.DataFrame(), "", ""

def get_db_history(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        time.sleep(random.uniform(0.2, 0.5)) # 連続アクセス防止
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'EUC-JP'
        if res.status_code != 200: return pd.DataFrame()

        tables = pd.read_html(io.StringIO(res.text))
        for tbl in tables:
            cols = [str(c) for c in tbl.columns]
            if any("日付" in c for c in cols) or any("着順" in c for c in cols):
                if len(tbl) > 2:
                    return tbl.head(10).astype(str).copy()
    except:
        pass
    return pd.DataFrame()

# --- メインロジック ---
url_input = st.text_input("netkeiba 出馬表URL", placeholder="https://race.netkeiba.com/race/shutuba.html?race_id=...")

if st.button("🔥 究極解析を開始する"):
    if not api_key:
        st.error("APIキーを設定してください。")
    elif not url_input:
        st.warning("解析するレースのURLを入力してください。")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            with st.status("🚀 現場急行中...", expanded=True) as status:
                st.write("🏁 出馬表をスキャン中...")
                df_horses, race_name, race_info = get_horse_list(url_input)
                
                if df_horses.empty:
                    st.error("馬のリストを取得できませんでした。")
                    st.stop()

                all_results = []
                total = len(df_horses)
                st.write(f"📊 {race_name} ({total}頭) の過去5走を精査中...")
                
                progress_bar = st.progress(0)
                for i, row in df_horses.iterrows():
                    history = get_db_history(row['URL'])
                    if not history.empty:
                        history['馬名'] = row['馬名']
                        all_results.append(history)
                        st.write(f"✅ {row['馬名']} のデータを解析ラインへ転送...")
                    else:
                        st.write(f"⚠️ {row['馬名']} の戦績取得に失敗（スキップ）")
                    
                    progress_bar.progress((i + 1) / total)
                
                status.update(label="収集完了！伝説の馬券師にデータを渡しました。", state="complete")

            if not all_results:
                st.error("有効な戦績データが取得できませんでした。時間をおいて再度お試しください。")
                st.stop()

            # AI解析フェーズ
            final_df = pd.concat(all_results, ignore_index=True)
            csv_text = final_df.to_csv(index=False)

            prompt = f"""
            # 役割
            あなたは30年のキャリアを持つ「伝説の馬券師」です。
            提供された戦績CSVデータを一頭ずつ精査し、期待値の高い馬を炙り出してください。

            # 現場情報
            レース名: {race_name}
            コンディション: {race_info}

            # 解析の指示
            1. 【ラップ・適性解析】: 当日の馬場状態(芝・ダート、重さ)と過去の走破タイムを照らし合わせよ。
            2. 各馬の「近走着順」だけでなく「上がり3F」「通過順」から展開を読み解け。
            3. 今回の馬場状態（{race_info}）に最も適性がある馬を特定せよ。
            4. 以下の印を打て：◎(本命)、○(対抗)、▲(単穴3頭)、☆(激穴)
            5. 「買い目」: 予算1万円で最も回収率を狙える馬券構成を具体的に提示せよ。

            # 戦績データ(CSV)
            {csv_text}
            """

            with st.spinner("🤖 伝説の馬券師がパドックを凝視中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"システムエラー: {e}")