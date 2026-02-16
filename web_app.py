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

COLUMNS = ["日付", "借方", "借方金額", "貸方", "貸方金額", "摘要"]

if 'journals_df' not in st.session_state:
    df = load_github_csv(JOURNAL_FILE)
    if not df.empty and "金額" in df.columns:
        df = df.rename(columns={"金額": "借方金額"})
        df["貸方金額"] = df["借方金額"]
    st.session_state.journals_df = df if not df.empty else pd.DataFrame(columns=COLUMNS)

if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
if 'multi_row_mode' not in st.session_state:
    st.session_state.multi_row_mode = False

# --- 金額のリアルタイム同期ロジック ---
def sync_amounts(source):
    if source == "deb":
        st.session_state.cre_a = st.session_state.deb_a
    else:
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
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            debit_sub = st.selectbox("借方科目", account_list, key="deb_s")
        with c2:
            debit_amt = st.number_input("借方金額", min_value=0, step=1, key="deb_a", on_change=sync_amounts, args=("deb",))
        with c3:
            credit_sub = st.selectbox("貸方科目", account_list, key="cre_s")
        with c4:
            credit_amt = st.number_input("貸方金額", min_value=0, step=1, key="cre_a", on_change=sync_amounts, args=("cre",))

        memo = st.text_input("摘要 (MEMO)")
        
        # セッション状態から最新値を取得
        d_val = st.session_state.get('deb_a', 0)
        c_val = st.session_state.get('cre_a', 0)
        is_balanced = (d_val > 0 and d_val == c_val)
        
        if st.button("リストに追加 (Add to list)", disabled=not is_balanced):
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit_sub, d_val, credit_sub, c_val, memo]], 
                                   columns=COLUMNS)
            st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            
            # --- 【修正点】安全なリセット処理 ---
            if 'deb_a' in st.session_state: st.session_state.deb_a = 0
            if 'cre_a' in st.session_state: st.session_state.cre_a = 0
            
            st.rerun()
            
    else:
        st.info("複数行仕訳モード：UI構築準備中")

    # --- 送信待ち・履歴表示セクション（維持） ---
    st.subheader("送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0] 
        h = st.columns(cols_w)
        h[0].caption("日付"); h[1].caption("借方"); h[2].caption("金額"); h[3].caption("貸方"); h[4].caption("金額"); h[5].caption("摘要")
        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            vals = [row['日付'], row['借方'], f"{row['借方金額']:,}", row['貸方'], f"{row['貸方金額']:,}", row['摘要']]
            for idx, val in enumerate(vals):
                c[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if c[6].button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("🚀 GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            repo.update_file(JOURNAL_FILE, "Fix: Safe reset logic", final_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
            st.rerun()

    st.divider()
    st.subheader("保存済み履歴 (HISTORY)")
    if not st.session_state.journals_df.empty:
        th = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
        th[0].caption("日付"); th[1].caption("借方"); th[2].caption("金額"); th[3].caption("貸方"); th[4].caption("金額"); th[5].caption("摘要")
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
            d_amt = row.get('借方金額', row.get('金額', 0))
            c_amt = row.get('貸方金額', row.get('金額.1', d_amt))
            fields = [row['日付'], row['借方'], f"{d_amt:,}", row['貸方'], f"{c_amt:,}", row['摘要'] if pd.notna(row['摘要']) else '']
            for idx, val in enumerate(fields):
                tr[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if tr[6].button("削除", key=f"h_del_{i}"):
                updated_df = st.session_state.journals_df.drop(i).reset_index(drop=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                repo.update_file(JOURNAL_FILE, "Delete row", updated_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
                st.session_state.journals_df = updated_df
                st.rerun()
