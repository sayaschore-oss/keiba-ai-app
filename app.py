import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇")
st.title("🏇 伝説の馬券師AI - 究極解析")
st.caption("netkeibaの出馬表URLを貼るだけで、最新のGemini 3.1 Proが分析します。")

# --- 設定エリア (サイドバー) ---
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Google API Keyを入力", type="password")
    model_name = st.selectbox("モデル選択", ["models/gemini-3.1-pro-preview", "models/gemini-3.1-flash-lite"])
    st.info("APIキーは一度入力すれば、このセッション中は有効です。")

def get_horse_list(url):
    """出馬表から馬名・URL・当日の馬場情報を抜き出す"""
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
    """馬の過去成績を取得"""
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    res.encoding = 'EUC-JP'
    tables = pd.read_html(io.StringIO(res.text))
    for tbl in tables:
        if '日付' in tbl.columns or '着順' in tbl.columns:
            return tbl.head(5).copy()
    return pd.DataFrame()

# --- メイン画面 ---
race_url = st.text_input("netkeibaの出馬表URLを入力例: https://race.netkeiba.com/race/shutuba.html?race_id=...")

if st.button("🔥 解析開始"):
    if not api_key:
        st.error("APIキーを入力してください。")
    elif not race_url:
        st.error("URLを入力してください。")
    else:
        try:
            # AIの設定
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            with st.status("データを収集中...", expanded=True) as status:
                st.write("🏁 出馬表を取得中...")
                df_horses, race_name, race_info = get_horse_list(race_url)
                st.write(f"📊 {race_name} ({len(df_horses)}頭) を確認")
                
                all_results = []
                progress_bar = st.progress(0)
                
                for i, row in df_horses.iterrows():
                    name = row['馬名']
                    st.write(f"🔍 {name} のデータを取得中...")
                    history = get_db_history(row['URL'])
                    if not history.empty:
                        history['馬名'] = name
                        all_results.append(history)
                    progress_bar.progress((i + 1) / len(df_horses))
                    time.sleep(0.1) # サーバー負荷軽減
                
                status.update(label="収集完了！AI分析を開始します...", state="complete")

            # CSV化
            final_df = pd.concat(all_results)
            csv_text = final_df.to_csv(index=False)

            # プロンプト
            prompt = f"""
            # 伝説の馬券師AI
            レース: {race_name} / 状況: {race_info}
            以下のデータに基づき、◎、○、▲(3頭)、☆を決定し、期待値のバグを指摘せよ。
            {csv_text}
            """

            with st.spinner("🤖 AIが考え中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.markdown(response.text)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")