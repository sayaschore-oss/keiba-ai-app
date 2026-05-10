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
st.caption("netkeibaの出馬表から、最新AIが「期待値のバグ」を炙り出します。")

# --- 設定エリア ---
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
    """出馬表から馬名とURLを取得"""
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
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
                if name:
                    full_url = "https://db.netkeiba.com" + a_tag['href'] if a_tag['href'].startswith("/") else a_tag['href']
                    data.append({'馬名': name, 'URL': full_url})
    
    df = pd.DataFrame(data).drop_duplicates(subset=['馬名']).reset_index(drop=True)
    return df, race_name, race_info

def get_db_history(url):
    """馬の戦績を確実に取得する(強化版)"""
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        res.encoding = 'EUC-JP'
        # 1. まず全てのテーブルを読み込む
        tables = pd.read_html(io.StringIO(res.text))
        
        for tbl in tables:
            # カラム名を文字列に変換してチェック（エラー回避）
            cols = [str(c) for c in tbl.columns]
            # 「日付」が含まれる、または「着順」が含まれる大きなテーブルを探す
            if any("日付" in c for c in cols) or any("着順" in c for c in cols):
                # 取得できたテーブルが小さすぎる場合は無視
                if len(tbl) > 1:
                    return tbl.head(10).astype(str).copy() # 全て文字列にしてAIに渡しやすくする
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
                    st.error("馬のリストが見つかりませんでした。")
                    st.stop()

                all_results = []
                total = len(df_horses)
                st.write(f"📊 {race_name} ({total}頭) の戦績を調査中...")
                
                progress_bar = st.progress(0)
                for i, row in df_horses.iterrows():
                    history = get_db_history(row['URL'])
                    if not history.empty:
                        history['馬名'] = row['馬名']
                        all_results.append(history)
                    progress_bar.progress((i + 1) / total)
                    time.sleep(0.1) # サーバー負荷を考慮
                
                status.update(label="データ収集完了！AIが買い目を作成中...", state="complete")

            if not all_results:
                st.error("有効な戦績データが取得できませんでした。URLがdb.netkeibaではなくrace.netkeibaの出馬表であることを確認してください。")
                st.stop()

            # 全データを結合
            final_df = pd.concat(all_results, ignore_index=True)
            csv_text = final_df.to_csv(index=False)

            prompt = f"""
            あなたは伝説の馬券師。
            レース: {race_name}
            状況: {race_info}
            
            # 指示 (Chain of Thought)
            1. 【ラップ・適性解析】: 当日の馬場状態(芝・ダート、重さ)と過去の走破タイムを照らし合わせよ。
            2. 【定性情報の深掘り】: ラボ情報から「陣営の勝負気配」を読み取れ。
            3. 【総合評価】: ◎、○、▲(3頭)、☆ を選出。
            4. 【期待値の歪み】: 前走不利や馬場適性から、世間が軽視している「バグ馬」を特定せよ。
            5. 【推奨買い目】: 具体的なフォーメーション。

            # 戦績データ(CSV)
            {csv_text}
            """

            with st.spinner("🤖 AI馬券師が思案中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"システムエラー: {e}")