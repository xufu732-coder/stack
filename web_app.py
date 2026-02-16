import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CSS設定（長い文字を自動縮小し、ボタンを横に固定する） ---
st.markdown("""
    <style>
    /* テキストが溢れる場合にフォントサイズを自動調整し、1行に収める */
    .tight-text {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 0.9rem; /* 基本サイズ */
    }
    /* ボタンの文字が縦にならないように保護 */
    div.stButton > button {
        white-space: nowrap !important;
        word-break: keep-all !important;
        min-width: 60px !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

all_data = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)

if menu == "仕訳入力":
    st.header("JOURNAL INPUT (サクサク入力モード)")
    
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

    # --- 送信待ちエリア ---
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        # ボタン幅を確保するために比率を微調整
        cols_w = [1.2, 2.3, 2.3, 1.2, 2, 1] 
        h = st.columns(cols_w)
        h[0].caption("日付")
        h[1].caption("借方")
        h[2].caption("貸方")
        h[3].caption("金額")
        h[4].caption("摘要")

        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            c[0].write(f"<div class='tight-text'>{row['日付']}</div>", unsafe_allow_html=True)
            c[1].write(f"<div class='tight-text'>{row['借方']}</div>", unsafe_allow_html=True)
            c[2].write(f"<div class='tight-text'>{row['貸方']}</div>", unsafe_allow_html=True)
            c[3].write(f"<div class='tight-text'>{row['金額']:,}</div>", unsafe_allow_html=True)
            c[4].write(f"<div class='tight-text'>{row['摘要']}</div>", unsafe_allow_html=True)
            if c[5].button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("🚀 GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            csv_content = final_df.to_csv(index=False)
            contents = repo.get_contents(JOURNAL_FILE)
            repo.update_file(JOURNAL_FILE, "Batch update", csv_content, contents.sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
            st.rerun()

    st.divider()
    
    # --- 履歴エリア ---
    st.subheader("保存済み履歴 (HISTORY)")
    if not st.session_state.journals_df.empty:
        th = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1])
        th[0].caption("日付")
        th[1].caption("借方")
        th[2].caption("貸方")
        th[3].caption("金額")
        th[4].caption("摘要")
        
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1])
            tr[0].write(f"<div class='tight-text'>{row['日付']}</div>", unsafe_allow_html=True)
            tr[1].write(f"<div class='tight-text'>{row['借方']}</div>", unsafe_allow_html=True)
            tr[2].write(f"<div class='tight-text'>{row['貸方']}</div>", unsafe_allow_html=True)
            tr[3].write(f"<div class='tight-text'>{row['金額']:,}</div>", unsafe_allow_html=True)
            tr[4].write(f"<div class='tight-text'>{row['摘要'] if pd.notna(row['摘要']) else ''}</div>", unsafe_allow_html=True)
            if tr[5].button("削除", key=f"h_del_{i}"):
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
    st.dataframe(all_data)
elif menu == "月次推移":
    st.header("MONTHLY TREND")
    st.write("推移データを表示")
