import streamlit as st
import pandas as pd
import os

st.title("🧧 会計入力アプリ (CSV管理版)")

# --- CSVから科目を読み込む ---
csv_file = 'categories.csv'

if os.path.exists(csv_file):
    # CSVが存在すれば読み込む
    df_cat = pd.read_csv(csv_file)
    category_list = df_cat['勘定科目'].tolist()
else:
    # CSVがない場合の予備
    category_list = ["現金", "普通預金"]

# --- 入力フォーム ---
with st.form("input_form"):
    date = st.date_input("日付")
    debit_category = st.selectbox("借方科目", options=category_list)
    credit_category = st.selectbox("貸方科目", options=category_list)
    amount = st.number_input("金額", min_value=0, step=100)
    submit_button = st.form_submit_button("入力を確定する")

if submit_button:
    st.success(f"{date} の入力を受け付けました！")
    st.balloons()
