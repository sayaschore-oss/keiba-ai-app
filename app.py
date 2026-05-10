import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇")
st.title("🏇 伝説의 馬券師AI - 究極解析")
st.caption("netkeibaの出馬表から、最新AIが「期待値のバグ」を炙り出します。")

# --- 設定エリア (Secrets対応) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = None

with st.sidebar:
    st.header("設定")
    if not api_key:
        api_key = st.text_input("Google API Keyを入力", type="password")
    else:
        st.success("✅ APIキーは自動適用されています")
    model_name = st.selectbox("モデル選択", ["models/gemini-3.1-flash-lite", "models/gemini-3.1-pro-preview"])

def get_horse_list(url):
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    res.encoding = 'EUC-JP'
    soup = BeautifulSoup(res.text, 'html.parser')
    race_name = soup.select_one(".RaceName").get_text(strip=True) if soup.select_one(".RaceName") else "不明なレース"
    race_data_tag = soup.select_one(".RaceData01")
    race_info = race_data_tag.get_text(strip=True) if race_data_tag else "情報なし"
    data = []
    rows = soup.select("tr.HorseList")
    for row in rows:
        target_td = row.select_one("td.HorseInfo")
        if target_td:
            a_tag = target_td.find("a", href=True)
            if a_tag:
                name = a_tag.text.strip()
                href = a_tag['href']
                if name and "/horse/" in href:
                    full_url = "https://db.netkeiba.com" + href if href.startswith("/") else href
                    data.append({'馬名': name, 'URL': full_url})
    return pd.DataFrame(data).drop_duplicates(subset=['馬名']).reset_index(drop=True), race_name, race_info

def get_db_history(url):
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        res.encoding = 'EUC-JP'
        tables = pd.read_html(io.StringIO(res.text))
        for tbl in tables:
            if '日付' in tbl.columns or '着順' in tbl.columns:
                return tbl.head(5).copy()
    except:
        pass
    return pd.DataFrame()

# --- メイン画面 ---
race_url = st.text_input("netkeibaの出馬表URLを入力", placeholder="https://race.netkeiba.com/race/shutuba.html?race_id=...")

if st.button("🔥 解析開始"):
    if not api_key:
        st.error("APIキーが設定されていません。")
    elif not race_url:
        st.error("URLを入力してください。")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            with st.status("データを解析中...", expanded=True) as status:
                st.write("🏁 出馬表を取得中...")
                df_horses, race_name, race_info = get_horse_list(race_url)
                
                if df_horses.empty:
                    st.error("馬名リストが取得できませんでした。")
                    st.stop()

                st.write(f"📊 {race_name} ({len(df_horses)}頭) の戦績を調査中...")
                
                all_results = []
                progress_bar = st.progress(0)
                
                for i, row in df_horses.iterrows():
                    history = get_db_history(row['URL'])
                    if not history.empty:
                        history['馬名'] = row['馬名']
                        all_results.append(history)
                    progress_bar.progress((i + 1) / len(df_horses))
                    time.sleep(0.05)
                
                # ここが修正箇所（107行目付近）
                status.update(label="データ収集完了！AIが買い目を作成中...", state="complete")

            if not all_results:
                st.error("戦績データが取得できませんでした。")
                st.stop()

            final_df = pd.concat(all_results)
            csv_text = final_df.to_csv(index=False)

            prompt = f"""
            # 役割
            あなたは伝説の馬券師。
            レース: {race_name} / 状況: {race_info}
            データ(CSV)から、◎、○、▲(3頭)、☆を選出し、期待値のバグを指摘せよ。
            最後に推奨買い目を提示せよ。
            {csv_text}
            """

            with st.spinner("🤖 AI馬券師が思案中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"システムエラー: {e}")