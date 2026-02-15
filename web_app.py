import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse # ←これが必要になりました

# ページ設定
st.set_page_config(page_title="会計アプリ", page_icon="🧧")
st.title("🧧 会計入力アプリ")

# --- 設定：スプレッドシートのURLを直接指定 ---
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1-4WPWmJEAI2jIoE7poCSOEKfqSIFMf2mn_U_EkCQ1X4/export?format=csv"

# Google Sheetsへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# マスターデータの読み込み
try:
    # 日本語のシート名を安全に読み込むためのおまじない
    master_sheet = urllib.parse.quote("マスター")
    master_df = conn.read(spreadsheet=spreadsheet_url, worksheet=master_sheet)
    category_list = master_df["勘定科目"].dropna().tolist()
except Exception as e:
    st.error(f"スプレッドシートの読み込みに失敗しました。")
    st.info(f"エラー詳細: {e}")
    st.stop()

st.header("新規仕訳入力")

with st.form("input_form"):
    date = st.date_input("日付")
    debit_category = st.selectbox("借方科目", options=category_list)
    credit_category = st.selectbox("貸方科目", options=category_list)
    amount = st.number_input("金額", min_value=0, step=100)
    description = st.text_input("摘要")
    submit_button = st.form_submit_button("スプレッドシートに登録")

if submit_button:
    new_data = pd.DataFrame([{
        "日付": str(date),
        "借方科目": debit_category,
        "貸方科目": credit_category,
        "金額": amount,
        "摘要": description
    }])
    
    try:
        # 登録時も日本語シート名を安全に指定
        journal_sheet = urllib.parse.quote("仕訳帳")
        existing_data = conn.read(spreadsheet=spreadsheet_url, worksheet=journal_sheet)
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        conn.update(spreadsheet=spreadsheet_url, worksheet=journal_sheet, data=updated_data)
        st.success("正常に登録されました！")
        st.balloons()
    except Exception as e:
        st.error(f"登録中にエラーが発生しました: {e}")




