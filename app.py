import streamlit as st
import pandas as pd
import io
import google.generativeai as genai

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇")
st.title("🏇 伝説の馬券師AI - 究極解析")
st.caption("自動取得がブロックされる場合でも、コピペで確実に解析可能です。")

# --- 設定エリア ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = None

with st.sidebar:
    st.header("⚙️ 設定")
    if not api_key:
        api_key = st.text_input("Google API Keyを入力", type="password")
    else:
        st.success("✅ APIキー適用済み")
    model_name = st.selectbox("AIモデル選択", ["models/gemini-3.1-flash-lite", "models/gemini-3.1-pro-preview"])

# --- メイン画面 ---
st.info("💡 使い方：netkeibaの『出馬表』や『戦績テーブル』をスマホで全選択してコピーし、下の枠に貼り付けてください。")
raw_data = st.text_area("ここにコピーしたデータを貼り付け", height=300, placeholder="ここにnetkeibaのテキストをそのままペースト...")

if st.button("🔥 伝説の予想を開始"):
    if not api_key:
        st.error("APIキーを設定してください。")
    elif not raw_data:
        st.warning("解析するデータを貼り付けてください。")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)

            prompt = f"""
            # 役割
            あなたは30年のキャリアを持つ「伝説の馬券師」です。
            以下のテキストデータ（netkeibaからコピーされたもの）を解析し、勝てる買い目を提示してください。

            # 解析の指示
            1. 【ラップ・適性解析】: 当日の馬場状態(芝・ダート、重さ)と過去の走破タイムを照らし合わせよ。
            2. ぐちゃぐちゃなテキストから馬名、近走成績、条件を読み取れ。
            3. ◎(本命)、○(対抗)、▲(単穴)、☆(穴) を選出せよ。
            4. 期待値のバグがある馬を特定し、プロの視点で解説せよ。
            5. 最後に具体的で「勝てる」推奨買い目を提示せよ。

            # 解析対象データ
            {raw_data}
            """

            with st.spinner("🤖 伝説の馬券師がデータを精査中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")