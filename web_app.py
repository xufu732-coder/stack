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

if 'master_df' not in st.session_state:
    st.session_state.master_df = load_github_csv(MASTER_FILE)
if 'journals_df' not in st.session_state:
    st.session_state.journals_df = load_github_csv(JOURNAL_FILE)
if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
if 'multi_row_mode' not in st.session_state:
    st.session_state.multi_row_mode = False

# ② 金額同期用のセッション状態
if 'sync_amount' not in st.session_state:
    st.session_state.sync_amount = None

account_list = st.session_state.master_df["勘定科目"].tolist() if not st.session_state.master_df.empty else []

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

all_data = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)

if menu == "仕訳入力":
    col_header, col_toggle = st.columns([3, 1])
    with col_header:
        mode_label = "複数行仕訳モード" if st.session_state.multi_row_mode else "サクサク入力モード"
        st.header(f"JOURNAL INPUT ({mode_label})")
    with col_toggle:
        if st.button("モード切替"):
            st.session_state.multi_row_mode = not st.session_state.multi_row_mode
            st.rerun()

    # --- ① 入力エリアの配置変更 ---
    date = st.date_input("日付", value=datetime.now())

    if not st.session_state.multi_row_mode:
        # 中段：借方・貸方の科目と金額（4カラム構成）
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            debit_sub = st.selectbox("借方科目", account_list, key="deb_s")
        with c2:
            # ② 金額の自動同期ロジック
            debit_amt = st.number_input("借方金額", min_value=0, step=1, value=st.session_state.sync_amount, key="deb_a")
        with c3:
            credit_sub = st.selectbox("貸方科目", account_list, key="cre_s")
        with c4:
            credit_amt = st.number_input("貸方金額", min_value=0, step=1, value=st.session_state.sync_amount, key="cre_a")

        # 金額が入力されたら同期用変数を更新
        if debit_amt != st.session_state.sync_amount:
            st.session_state.sync_amount = debit_amt
            st.rerun()
        elif credit_amt != st.session_state.sync_amount:
            st.session_state.sync_amount = credit_amt
            st.rerun()

        # 下段：摘要
        memo = st.text_input("摘要 (MEMO)")
        
        if st.button("リストに追加 (Add to list)"):
            if st.session_state.sync_amount and st.session_state.sync_amount > 0:
                new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit_sub, st.session_state.sync_amount, credit_sub, st.session_state.sync_amount, memo]], 
                                       columns=st.session_state.temp_journals.columns)
                st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
                st.session_state.sync_amount = None # 登録後は金額クリア
                st.rerun()
    else:
        st.info("複数行仕訳モード：UI構築準備中")

    # --- ③ 登録、仮登録欄の調整（表示形式を維持しつつデータ反映） ---
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.3, 2.3, 1.2, 2, 1] 
        h = st.columns(cols_w)
        h[0].caption("日付"); h[1].caption("借方"); h[2].caption("貸方"); h[3].caption("金額"); h[4].caption("摘要")

        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            # 借方・貸方・金額の並びを反映
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

# 以降のメニューは変更なし
elif menu == "マスター確認":
    st.header("MASTER DATA")
    st.dataframe(st.session_state.master_df)
elif menu == "財務諸表":
    st.header("FINANCIAL STATEMENTS")
    st.dataframe(all_data)
elif menu == "月次推移":
    st.header("MONTHLY TREND")
    st.write("推移データを表示")
