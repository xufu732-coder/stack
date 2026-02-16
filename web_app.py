import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="簡易会計ソフト", page_icon="📝")
st.title("📝 みんなの仕訳帳アプリ")

# --- 1. 勘定科目の読み込み (categories.csv) ---
try:
    df_cat = pd.read_csv('categories.csv')
    category_list = df_cat['勘定科目'].tolist()
except:
    category_list = ["現金", "普通預金", "売上高"]

# --- 2. データの保存場所を作る ---
# ページをリロードしてもデータが消えないように st.session_state を使います
if 'journal_data' not in st.session_state:
    st.session_state.journal_data = pd.DataFrame(columns=["日付", "借方科目", "貸方科目", "金額", "摘要"])

# --- 3. 入力フォーム ---
st.header("📥 仕訳入力")
with st.form("input_form", clear_on_submit=True):
    date = st.date_input("日付", value=datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        debit = st.selectbox("借方科目（左）", category_list)
    with col2:
        credit = st.selectbox("貸方科目（右）", category_list)
    
    amount = st.number_input("金額 (円)", min_value=0, step=1000)
    description = st.text_input("摘要（メモ）")
    
    submit = st.form_submit_button("記帳する（保存）")

# --- 4. 保存ボタンが押された時の処理 ---
if submit:
    new_data = {
        "日付": date.strftime('%Y-%m-%d'),
        "借方科目": debit,
        "貸方科目": credit,
        "金額": amount,
        "摘要": description
    }
    # データを蓄積
    st.session_state.journal_data = pd.concat([st.session_state.journal_data, pd.DataFrame([new_data])], ignore_index=True)
    st.success("記帳しました！")
    st.balloons()

# --- 5. 溜まったデータを表示する ---
st.header("📖 これまでの仕訳一覧")
if not st.session_state.journal_data.empty:
    st.dataframe(st.session_state.journal_data, use_container_width=True)
    
    # CSVとしてダウンロードするボタン
    csv = st.session_state.journal_data.to_csv(index=False).encode('utf_8_sig')
    st.download_button(
        label="データをCSVでダウンロード",
        data=csv,
        file_name='my_journal.csv',
        mime='text/csv',
    )
else:
    st.info("まだデータがありません。上のフォームから入力してみてね！")
