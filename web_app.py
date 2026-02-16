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

# 表示用統合データ
all_data = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)

if menu == "仕訳入力":
    st.header("JOURNAL INPUT (サクサク入力モード)")
    
    # 入力欄
    date = st.date_input("日付", value=datetime.now())
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        debit = st.selectbox("借方科目 (DEBIT)", account_list)
        amount = st.number_input("金額", min_value=0, step=1, value=None)
    with col_in2:
        credit = st.selectbox("貸方科目 (CREDIT)", account_list)
        memo = st.text_input("摘要 (MEMO)")
    
    if st.button("リストに追加 (Add to list)"):
        if amount and amount > 0:
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                                   columns=st.session_state.temp_journals.columns)
            st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            st.rerun()

    # 送信待ちエリア
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        for i, row in st.session_state.temp_journals.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 1.5, 2, 1])
            c1.text(row['日付'])
            c2.text(row['借方'])
            c3.text(f"{row['金額']:,}")
            c4.text(row['貸方'])
            if c5.button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("🚀 GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            csv_content = final_df.to_csv(index=False)
            contents = repo.get_contents(JOURNAL_FILE)
            repo.update_file(JOURNAL_FILE, "Update", csv_content, contents.sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
            st.rerun()

    st.divider()
    
    # 履歴エリア：Excel感を消し、縦のラインを揃える
    st.subheader("保存済み履歴 (HISTORY)")
    if st.button("【警告】全履歴削除"):
        # 削除ロジック（中身省略、既存のまま）
        pass

    if not st.session_state.journals_df.empty:
        # ヘッダー（縦を揃えるためのガイド）
        h1, h2, h3, h4, h5, h6 = st.columns([1.5, 2, 1.2, 2, 2.3, 1])
        h1.caption("日付")
        h2.caption("借方")
        h3.caption("金額")
        h4.caption("貸方")
        h5.caption("摘要")
        
        # 履歴を1行ずつ表示
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1.5, 2, 1.2, 2, 2.3, 1])
            r1.text(row['日付'])
            r2.text(row['借方'])
            r3.text(f"{row['金額']:,}")
            r4.text(row['貸方'])
            r5.text(row['摘要'] if pd.notna(row['摘要']) else "")
            if r6.button("削除", key=f"h_del_{i}"):
                # 個別削除ロジック（既存のまま）
                updated_df = st.session_state.journals_df.drop(i).reset_index(drop=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                csv_content = updated_df.to_csv(index=False)
                contents = repo.get_contents(JOURNAL_FILE)
                repo.update_file(JOURNAL_FILE, "Delete row", csv_content, contents.sha)
                st.session_state.journals_df = updated_df
                st.rerun()

elif menu == "マスター確認":
    st.header("MASTER DATA")
    st.dataframe(st.session_state.master_df)

elif menu == "財務諸表":
    st.header("FINANCIAL STATEMENTS")
    # ここに以前の集計ロジックが入ります。all_data を使って計算してください。
    st.dataframe(all_data)

elif menu == "月次推移":
    st.header("MONTHLY TREND")
    # ここに以前の推移ロジックが入ります。
    st.write("推移グラフを表示...")
