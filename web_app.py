import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Accounting Web", page_icon="🧧")
st.title("🧧 Accounting Web")

# Google Sheetsへの接続
conn = st.connection("gsheets", type=GSheetsConnection)

# マスターの読み込み
try:
    # URLはSecretsから自動で読み込まれます
    master_df = conn.read(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], worksheet="マスター")
    category_list = master_df["勘定科目"].dropna().tolist()
except Exception as e:
    st.error(f"マスターの読み込みに失敗しました。スプレッドシートのシート名が「マスター」になっているか確認してください。")
    st.stop()

st.header("新規仕訳入力")

with st.form("input_form"):
    date = st.date_input("日付")
    debit_category = st.selectbox("借方科目", options=category_list)
    credit_category = st.selectbox("貸方科目", options=category_list)
    amount = st.number_input("金額", min_value=0, step=100)
    description = st.text_input("摘要")
    
    submit_button = st.form_submit_button("登録")

if submit_button:
    new_data = pd.DataFrame([{
        "日付": str(date),
        "借方科目": debit_category,
        "貸方科目": credit_category,
        "金額": amount,
        "摘要": description
    }])
    
    try:
        existing_data = conn.read(worksheet="仕訳帳")
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        conn.update(worksheet="仕訳帳", data=updated_data)
        st.success("スプレッドシートに登録しました！")
        st.balloons()
    except Exception as e:
        st.error(f"登録に失敗しました: {e}")

