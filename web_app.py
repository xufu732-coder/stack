import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- 設定 ---
DATA_FILE = "journals.json"
MASTER_FILE = "会計.xlsm"

# --- 元のロジックをそのまま流用 ---
def load_master():
    try:
        df = pd.read_excel(MASTER_FILE, sheet_name="マスター")
        return df, df.set_index("勘定科目").to_dict(orient="index"), df["勘定科目"].tolist()
    except Exception as e:
        st.error(f"マスター読み込み失敗: {e}")
        return None, {}, []

def load_journals():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_journals(journals):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(journals, f, ensure_ascii=False, indent=4)

# --- 画面表示設定 ---
st.set_page_config(page_title="P5 Accounting Web", layout="centered")

# デザイン調整
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .stButton>button { background-color: #FF0000; color: white; font-weight: bold; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧧 Accounting Web")

master_df, master_data, account_list = load_master()
journals = load_journals()

# --- 修正ポイント1: st.formを外して、即時反映＆Enter対応にする ---
st.subheader("新規仕訳入力")

date = st.date_input("日付", datetime.now())
debit = st.selectbox("借方科目", account_list)
credit = st.selectbox("貸方科目", account_list)

# --- 修正ポイント2: value=None にすることで初期値を空にし、入力しやすくする ---
amount = st.number_input("金額", min_value=0, step=1000, value=None, placeholder="金額を入力...")

# 登録ボタン
if st.button("仕訳登録"):
    if amount is None or amount == 0:
        st.warning("金額を入力してください")
    else:
        new_entry = {
            "date": date.strftime("%Y-%m-%d"),
            "debit": debit, 
            "debit_amount": amount,
            "credit": credit, 
            "credit_amount": amount
        }
        journals.append(new_entry)
        save_journals(journals)
        st.success(f"登録完了: {amount:,}円")
        # 登録後に画面をリフレッシュして入力を空にする
        st.rerun()

st.divider()
st.subheader("最新の履歴")
if journals:
    df_hist = pd.DataFrame(journals).iloc[::-1].head(5)
    st.table(df_hist)