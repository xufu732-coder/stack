import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- 設定 & 接続 (変更なし) ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "xufu732-coder/stack" 
JOURNAL_FILE = "journal.csv"
MASTER_FILE = "categories.csv"

# --- データの読み込み (セッション管理で高速化) ---
if 'master_df' not in st.session_state:
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(MASTER_FILE)
        st.session_state.master_df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except: st.session_state.master_df = pd.DataFrame(columns=["勘定科目"])

if 'journals_df' not in st.session_state:
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(JOURNAL_FILE)
        st.session_state.journals_df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except: st.session_state.journals_df = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])

# 【一時保存リスト】ここに入力したデータが溜まります
if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])

account_list = st.session_state.master_df["勘定科目"].tolist()

# --- サイドメニュー ---
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("📥 JOURNAL INPUT (Enterで即追加)")
    
    # --- 入力エリア ---
    # st.formを使わないことで、Enterキーの反応を有効にします
    c0, c1, c2, c3, c4 = st.columns([1.5, 2, 1.5, 2, 2])
    
    with c0: date = st.date_input("日付", value=datetime.now())
    with c1: debit = st.selectbox("借方", account_list, key="sb_debit")
    with c2: amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="Enterで追加", key="num_amt")
    with c3: credit = st.selectbox("貸方", account_list, key="sb_credit")
    with c4: memo = st.text_input("摘要", placeholder="メモ", key="txt_memo")

    # --- 重要：Enter/ボタンが押された時の処理 ---
    # 金額欄や摘要欄でEnterを押すと、この下のロジックが走ります
    if amount and amount > 0:
        new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                               columns=st.session_state.temp_journals.columns)
        st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
        # 登録したら金額をリセットするためにRerun
        st.rerun()

    # --- 送信待ちリストの表示 ---
    st.divider()
    st.subheader("📝 送信待ちの仕訳 (GitHub未保存)")
    if not st.session_state.temp_journals.empty:
        st.dataframe(st.session_state.temp_journals, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🚀 一括保存", type="primary"):
                with st.spinner("GitHubへ送信中..."):
                    final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(REPO_NAME)
                    csv_content = final_df.to_csv(index=False)
                    contents = repo.get_contents(JOURNAL_FILE)
                    repo.update_file(JOURNAL_FILE, "Batch update", csv_content, contents.sha)
                    
                    st.session_state.journals_df = final_df
                    st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
                    st.success("GitHubへの保存が完了！")
                    st.rerun()
        with col_btn2:
            if st.button("リストを空にする"):
                st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
                st.rerun()
    else:
        st.info("金額を入力してEnterを押すと、ここに溜まります。")

    st.subheader("📖 保存済み履歴")
    st.dataframe(st.session_state.journals_df.iloc[::-1], use_container_width=True)

# 他のメニュー（財務諸表など）は一切変更していません。
