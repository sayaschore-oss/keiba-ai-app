import streamlit as st
import pandas as pd
import io
import google.generativeai as genai

# --- ページ設定 ---
st.set_page_config(page_title="伝説の馬券師AI", page_icon="🏇", layout="wide")
st.title("🏇 伝説の馬券師AI - 究極解析")
st.caption("コピペデータから『期待値のバグ』を精密に炙り出します。")

# --- 設定エリア (サイドバー) ---
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
    
    # モデル選択機能の追加
    model_name = st.selectbox(
        "AIモデル選択", 
        [
            "models/gemini-3.1-flash-lite",   # 爆速・軽量
            "models/gemini-3.1-pro-preview", # 【推奨】知能最高。馬番ミス防止に最適
            "models/gemini-2.5-pro"          # 安定版
        ],
        help="馬番の間違いを減らしたい時は『3.1-pro-preview』を選んでください。"
    )
    st.divider()
    st.info("netkeibaの出馬表を『全選択→コピー』して貼り付けてください。")

# --- メイン画面 ---
st.info("💡 使い方：netkeibaの『出馬表』ページをコピーして、下の枠に貼り付けてください。")
raw_data = st.text_area("ここにデータを貼り付け", height=400, placeholder="1 カヴァレリッツォ...\n2 オルネーロ...")

if st.button("🔥 究極解析を開始する"):
    if not api_key:
        st.error("APIキーを設定してください。")
    elif not raw_data:
        st.warning("解析するデータを貼り付けてください。")
    else:
        try:
            genai.configure(api_key=api_key)
            # 選択されたモデルを使用
            model = genai.GenerativeModel(model_name)

            # --- 最強のChain of Thoughtプロンプト ---
            prompt = f"""
            # 役割
            あなたは30年のキャリアを持つ「伝説の馬券師」です。
            提供されたぐちゃぐちゃなテキストデータから正確な情報を抽出し、プロの視点で予想を提供してください。

           # 指示 (Strict Chain of Thought / 思考の連鎖)
            # ステップ1：【出走馬名簿の強制書き出し】※最優先
            解析を始める前に、まず以下の手順を実行し、その結果を最初に出力せよ。
            1. 提供されたデータから「今回のレースの出走表（枠順）」のみを正確に抽出せよ。
            2. **重要：他レースの結果、過去の着順、オッズ（例: 26.5）、馬体重（例: 480）に含まれる数字を絶対に馬番（1〜18）と混同するな。**
            3. 確定した「馬番：馬名」のリストを全頭分、箇条書きで出力せよ。これが以降の解析の唯一の正解となる。

            # ステップ2：【多角的な解析】
            ステップ1で作成したリストの**全頭**について、以下の3項目を解析せよ。
            1. 【ラップ・適性解析】: 当日の馬場状態と過去の走破タイムを照らし合わせ、今回の展開への適合度を評価せよ。
            2. 【定性情報の深掘り】: テキスト内のコメントやラボ情報から「陣営の勝負気配」や「追い切りの良し悪し」を読み取れ。
            3. 【状態分析】: 馬体重の増減（＋10kg以上の太め残り、ー10kg以上の絞りすぎ）がある場合、評価に反映させよ。
            4. 【総評】: 期待値や展開面でのプラス・マイナス要素

            # ステップ3：【期待値とフィルター】
            1. 【危険な人気馬】: 人気でも不安要素（右回りが苦手、重馬場がダメ等）がある馬を特定し、評価を下げろ。
            2. 【期待値のバグ】: 前走不利や適性から、実力の割に売れていない（オッズが高すぎる）馬を1頭特定せよ。

            # ステップ4：【結論と買い目】
            1. 【総合評価】: ◎(本命)、○(対抗)、▲(単穴3頭)、☆(激走穴馬) を選出せよ。
            2. 【推奨買い目】: 予算5,000円で最も回収率を狙える具体的な買い目を出せ。
            3. **形式：必ず『馬番（馬名）』の形式（例: 1(カヴァレリッツォ)）で記述せよ。ステップ1の名簿にない馬番は1点たりとも使用禁止。**
            4. 【勝負のキモ】: このレースで最も注目すべき「一点の真実」を断言せよ。

            # 解析対象データ
            {raw_data}
            """

            with st.spinner(f"🤖 {model_name} が分析中..."):
                response = model.generate_content(prompt)
                st.markdown("---")
                st.subheader("✨ 伝説の予想レポート")
                st.write(response.text)

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")