import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import google.generativeai as genai
import time

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇")
st.title("🏇 伝説の馬券師AI - 究極解析") # タイトルを修正
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
    """出馬表から正確に馬名・URL・馬場情報を取得"""
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    res.encoding = 'EUC-JP'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    race_name = soup.select_one(".RaceName").get_text(strip=True) if soup.select_one(".RaceName") else "不明なレース"
    race_data_tag = soup.select_one(".RaceData01")
    race_info = race_data_tag.get_text(strip=True) if race_data_tag else "情報なし"
    
    data = []
    # 馬名が入っている行(tr.HorseList)だけに限定
    rows = soup.select("tr.HorseList")
    for row in rows:
        # 馬名セルのみを指定
        target_td = row.select_one("td.HorseInfo")
        if target_td:
            # セル内の最初のリンクのみを取得
            a_tag = target_td.find("a", href=True)
            if a_tag and "/horse/" in a_tag['href']:
                name = a_tag.text.strip()
                if name:
                    full_url = "https://db.netkeiba.com" + a_tag['href'] if a_tag['href'].startswith("/") else a_tag['href']
                    data.append({'馬名': name, 'URL': full_url})
    
    # 最後に重複を確実に排除
    df = pd.DataFrame(data).drop_duplicates(subset=['馬名']).reset_index(drop=True)
    return df, race_name, race_info

def get_db_history(url):
    """馬の過去成績を取得（エラーガード強化）"""
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        res.encoding = 'EUC-JP'
        # pandasのread_htmlでテーブルを抽出
        tables = pd.read_html(io.StringIO(res.text))
        for tbl in tables:
            # 戦績テーブル（日付や着順があるもの）を特定
            if '日付' in tbl.columns or '着順' in tbl.columns:
                # 必要な列が欠けている場合のエラー回避
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
                    st.error("馬のリストが見つかりませんでした。URLが正しいか確認してください。")
                    st.stop()

                total = len(df_horses)
                st.write(f"📊 {race_name} ({total}頭) の戦績を調査中...")
                
                all_results = []
                progress_bar = st.progress(0)
                
                for i, row in df_horses.iterrows():
                    history = get_db_history(row['URL'])
                    if not history.empty:
                        history['馬名'] = row['馬名']
                        all_results.append(history)
                    progress_bar.progress((i + 1) / total)
                    time.sleep(0.05)
                
                status.update(label="データ収集完了！AIが買い目を作成中...", state="complete")

            if not all_results:
                st.error("有効な戦績データが取得できませんでした。")
                st.stop()

            final_df = pd.concat(all_results, ignore_index=True)
            csv_text = final_df.to_csv(index=False)

            prompt = f"""
            # 役割
            あなたは伝説の馬券師。冷静かつ鋭い洞察で「期待値のバグ」を突く。
            
            # 現場情報
            レース: {race_name}
            コンディション: {race_info}

            # 指示
            1. 以下の戦績データ(CSV)を分析し、当日の馬場状態との相性を評価せよ。
            2. ◎、○、▲(3頭)、☆ を選出せよ。
            3. 選出理由を簡潔に、かつプロの視点で解説せよ。
            4. 最後に具体的で「勝てる」推奨買い目を提示せよ。

            # 戦績データ
            {csv_text}
            """

            with st.spinner("🤖 AI馬券師が思案中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"システムエラー: {e}")