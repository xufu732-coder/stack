import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- 設定 & 接続 ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "xufu732-coder/stack" 
JOURNAL_FILE = "journal.csv"
MASTER_FILE = "categories.csv"

def load_github_csv(file_name):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(file_name)
        return pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except: return pd.DataFrame()

if 'master_df' not in st.session_state:
    st.session_state.master_df = load_github_csv(MASTER_FILE)
if 'journals_df' not in st.session_state:
    st.session_state.journals_df = load_github_csv(JOURNAL_FILE)
if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])

account_list = st.session_state.master_df["勘定科目"].tolist() if not st.session_state.master_df.empty else []

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    # ③アイコンの廃止
    st.header("JOURNAL INPUT (サクサク入力モード)")
    
    date = st.date_input("日付", value=datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        debit = st.selectbox("借方科目 (DEBIT)", account_list)
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="金額入力後Enter")
    with col2:
        credit = st.selectbox("貸方科目 (CREDIT)", account_list)
        memo = st.text_input("摘要 (MEMO)")
    
    if st.button("リストに追加 (Add to list)"):
        if amount and amount > 0 and debit != credit:
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                                   columns=st.session_state.temp_journals.columns)
            st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            st.rerun()

    # ②仮記録済みの削除機能
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        # 個別削除用インデックス表示
        for i, row in st.session_state.temp_journals.iterrows():
            cols = st.columns([8, 1])
            cols[0].write(f"{row['日付']} | {row['借方']} {row['金額']:,} / {row['貸方']} | {row['摘要']}")
            if cols[1].button("消去", key=f"del_temp_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()

        if st.button("🚀 GitHubへ一括保存する (Save all to GitHub)"):
            with st.spinner("通信中..."):
                final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                csv_content = final_df.to_csv(index=False)
                contents = repo.get_contents(JOURNAL_FILE)
                repo.update_file(JOURNAL_FILE, "Batch update", csv_content, contents.sha)
                st.session_state.journals_df = final_df
                st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
                st.rerun()
        
        # ②仮記録済みの全削除
        if st.button("送信待ちリストを全削除"):
            st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
            st.rerun()

    st.divider()
    
    # ②記録済みの全削除
    st.subheader("保存済み履歴 (HISTORY)")
    if st.button("【警告】GitHub上の全履歴を削除"):
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        empty_df = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
        csv_content = empty_df.to_csv(index=False)
        contents = repo.get_contents(JOURNAL_FILE)
        repo.update_file(JOURNAL_FILE, "Delete all history", csv_content, contents.sha)
        st.session_state.journals_df = empty_df
        st.rerun()

    # ①一番右の金額欄の廃止
    if not st.session_state.journals_df.empty:
        # 金額.1列を除外して表示
        history_display = st.session_state.journals_df.drop(columns=["金額.1"])
        
        # ②記録済みの個別削除
        for i, row in history_display.iloc[::-1].iterrows():
            cols = st.columns([8, 1])
            cols[0].dataframe(pd.DataFrame([row]), hide_index=True)
            if cols[1].button("削除", key=f"del_hist_{i}"):
                updated_df = st.session_state.journals_df.drop(i).reset_index(drop=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                csv_content = updated_df.to_csv(index=False)
                contents = repo.get_contents(JOURNAL_FILE)
                repo.update_file(JOURNAL_FILE, f"Delete row {i}", csv_content, contents.sha)
                st.session_state.journals_df = updated_df
                st.rerun()

# マスター確認、財務諸表、月次推移の枠組みは維持
elif menu == "マスター確認":
    st.header("MASTER DATA")
    st.dataframe(st.session_state.master_df)
elif menu == "財務諸表":
    st.header("FINANCIAL STATEMENTS")
elif menu == "月次推移":
    st.header("MONTHLY TREND")
