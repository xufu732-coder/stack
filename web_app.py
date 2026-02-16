import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CSS設定（以前の調整を維持） ---
st.markdown("""
    <style>
    .tight-text {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 0.9rem;
    }
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

# 【新規】モード管理用セッション状態
if 'multi_row_mode' not in st.session_state:
    st.session_state.multi_row_mode = False

account_list = st.session_state.master_df["勘定科目"].tolist() if not st.session_state.master_df.empty else []

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

all_data = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)

if menu == "仕訳入力":
    # モード切り替えボタンの設置
    col_header, col_toggle = st.columns([3, 1])
    with col_header:
        mode_label = "複数行仕訳モード" if st.session_state.multi_row_mode else "サクサク入力モード"
        st.header(f"JOURNAL INPUT ({mode_label})")
    with col_toggle:
        if st.button("モード切替"):
            st.session_state.multi_row_mode = not st.session_state.multi_row_mode
            st.rerun()

    # --- 入力エリア ---
    date = st.date_input("日付", value=datetime.now())

    if not st.session_state.multi_row_mode:
        # 従来の単一行入力
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
    else:
        # 複数行仕訳モード（枠組みのみ設置）
        st.info("複数行仕訳モード：固定資産売却などの複雑な仕訳に対応予定です。現在はまだ入力ロジックを構築していません。")
        # TODO: 借方・貸方を複数行追加できるUIの実装

    # --- 送信待ちエリア / 履歴エリア（以前の修正を100%維持） ---
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.3, 2.3, 1.2, 2, 1] 
        h = st.columns(cols_w)
        h[0].caption("日付"); h[1].caption("借方"); h[2].caption("貸方"); h[3].caption("金額"); h[4].caption("摘要")

        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            for idx, val in enumerate([row['日付'], row['借方'], row['貸方'], f"{row['金額']:,}", row['摘要']]):
                c[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if c[5].button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("🚀 GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            repo.update_file(JOURNAL_FILE, "Batch update", final_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
            st.rerun()

    st.divider()
    st.subheader("保存済み履歴 (HISTORY)")
    if not st.session_state.journals_df.empty:
        th = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1])
        th[0].caption("日付"); th[1].caption("借方"); th[2].caption("貸方"); th[3].caption("金額"); th[4].caption("摘要")
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1])
            fields = [row['日付'], row['借方'], row['貸方'], f"{row['金額']:,}", row['摘要'] if pd.notna(row['摘要']) else '']
            for idx, val in enumerate(fields):
                tr[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if tr[5].button("削除", key=f"h_del_{i}"):
                updated_df = st.session_state.journals_df.drop(i).reset_index(drop=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                repo.update_file(JOURNAL_FILE, "Delete row", updated_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
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
