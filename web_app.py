import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CSS設定（維持） ---
st.markdown("""
    <style>
    .tight-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.9rem; }
    div.stButton > button { white-space: nowrap !important; word-break: keep-all !important; min-width: 60px !important; }
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

if 'journals_df' not in st.session_state:
    st.session_state.journals_df = load_github_csv(JOURNAL_FILE)
if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
if 'multi_row_mode' not in st.session_state:
    st.session_state.multi_row_mode = False

# --- 【修正】確実に連動させるためのコールバック ---
def sync_deb_to_cre():
    st.session_state.cre_a = st.session_state.deb_a

def sync_cre_to_deb():
    st.session_state.deb_a = st.session_state.cre_a

account_list = load_github_csv(MASTER_FILE)["勘定科目"].tolist() if 'master_df' not in st.session_state else st.session_state.master_df["勘定科目"].tolist()

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    col_header, col_toggle = st.columns([3, 1])
    with col_header:
        mode_label = "複数行仕訳モード" if st.session_state.multi_row_mode else "サクサク入力モード"
        st.header(f"JOURNAL INPUT ({mode_label})")
    with col_toggle:
        if st.button("モード切替"):
            st.session_state.multi_row_mode = not st.session_state.multi_row_mode
            st.rerun()

    date = st.date_input("日付", value=datetime.now())

    if not st.session_state.multi_row_mode:
        # 中段：4列構成
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            debit_sub = st.selectbox("借方科目", account_list, key="deb_s")
        with c2:
            # 借方入力 → 貸方を更新
            debit_amt = st.number_input("借方金額", min_value=0, step=1, key="deb_a", on_change=sync_deb_to_cre)
        with c3:
            credit_sub = st.selectbox("貸方科目", account_list, key="cre_s")
        with c4:
            # 貸方入力 → 借方を更新
            credit_amt = st.number_input("貸方金額", min_value=0, step=1, key="cre_a", on_change=sync_cre_to_deb)

        memo = st.text_input("摘要 (MEMO)")
        
        if st.button("リストに追加 (Add to list)"):
            if debit_amt and debit_amt > 0:
                new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit_sub, debit_amt, credit_sub, credit_amt, memo]], 
                                       columns=st.session_state.temp_journals.columns)
                st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
                # 登録後に金額をリセット
                st.session_state.deb_a = 0
                st.session_state.cre_a = 0
                st.rerun()
    else:
        st.info("複数行仕訳モード：UI構築準備中")

    # --- 送信待ちエリア / 履歴エリア（配置・デザイン維持） ---
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.3, 2.3, 1.2, 2, 1.2] 
        h = st.columns(cols_w)
        h[0].caption("日付"); h[1].caption("借方"); h[2].caption("貸方"); h[3].caption("金額"); h[4].caption("摘要")
        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            vals = [row['日付'], row['借方'], row['貸方'], f"{row['金額']:,}", row['摘要']]
            for idx, val in enumerate(vals):
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
        th = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1.2])
        th[0].caption("日付"); th[1].caption("借方"); th[2].caption("貸方"); th[3].caption("金額"); th[4].caption("摘要")
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.3, 2.3, 1.2, 2, 1.2])
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

# 財務諸表、マスター等は維持
elif menu == "マスター確認":
    st.header("MASTER DATA")
    st.dataframe(st.session_state.master_df)
elif menu == "財務諸表":
    st.header("FINANCIAL STATEMENTS")
    st.dataframe(pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True))
