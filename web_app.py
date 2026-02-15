import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="会計アプリ", page_icon="🧧")
st.title("🧧 会計入力アプリ（スプレッドシート不要版）")

# --- 設定：勘定科目をここに直接書く ---
# スプレッドシートの代わりに、ここで科目を管理します
category_list = [
    "現金", 
    "普通預金", 
    "売上高", 
    "仕入高", 
    "消耗品費", 
    "旅費交通費", 
    "通信費", 
    "支払家賃", 
    "雑費"
]

st.header("新規仕訳入力")

# 入力フォーム
with st.form("input_form"):
    date = st.date_input("日付")
    debit_category = st.selectbox("借方科目", options=category_list)
    credit_category = st.selectbox("貸方科目", options=category_list)
    amount = st.number_input("金額", min_value=0, step=100)
    description = st.text_input("摘要")
    submit_button = st.form_submit_button("入力を確定する")

# ボタンを押した時の動き
if submit_button:
    # 画面に結果を表示する（今は保存の代わりに表示だけします）
    st.success("入力内容を確認しました！")
    
    st.subheader("今回の入力内容")
    result_df = pd.DataFrame([{
        "日付": str(date),
        "借方": debit_category,
        "貸方": credit_category,
        "金額": f"{amount:,}円",
        "摘要": description
    }])
    st.table(result_df)
    
    st.balloons() # お祝いの風船！
