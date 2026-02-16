import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- CSS設定 ---
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

# データ読み込みと整数化
if 'journals_df' not in st.session_state:
    df = load_github_csv(JOURNAL_FILE)
    if not df.empty:
        if "金額" in df.columns:
            df = df.rename(columns={"金額": "借方金額", "金額.1": "貸方金額"})
        for col in ["借方金額", "貸方金額"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    st.session_state.journals_df = df if not df.empty else pd.DataFrame(columns=COLUMNS)

if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)

# マスターデータの読み込み
master_df = load_github_csv(MASTER_FILE)
account_list = master_df["勘定科目"].tolist() if not master_df.empty else []

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

# --- 仕訳入力画面 ---
if menu == "仕訳入力":
    st.header("JOURNAL INPUT")
    date = st.date_input("日付", value=datetime.now())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        debit_sub = st.selectbox("借方科目", account_list, key="deb_s")
    with c2:
        debit_amt = st.number_input("借方金額", min_value=0, step=1, key="deb_a")
    with c3:
        credit_sub = st.selectbox("貸方科目", account_list, key="cre_s")
    with c4:
        credit_amt = st.number_input("貸方金額", min_value=0, step=1, key="cre_a")

    memo = st.text_input("摘要 (MEMO)")
    
    if st.button("リストに追加"):
        if debit_amt > 0 or credit_amt > 0:
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit_sub, int(debit_amt), credit_sub, int(credit_amt), memo]], 
                                   columns=COLUMNS)
            st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            st.rerun()

    # --- 送信待ちエリア ---
    st.divider()
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("送信待ちの仕訳")
    with col_t2:
        if not st.session_state.temp_journals.empty:
            if st.button("リストを全削除", use_container_width=True):
                st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
                st.rerun()

    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0] 
        h = st.columns(cols_w)
        headers = ["日付", "借方", "借方額", "貸方", "貸方額", "摘要"]
        for idx, text in enumerate(headers): h[idx].caption(text)

        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            vals = [row['日付'], row['借方'], f"{int(row['借方金額']):,}", row['貸方'], f"{int(row['貸方金額']):,}", row['摘要']]
            for idx, val in enumerate(vals):
                c[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if c[6].button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            repo.update_file(JOURNAL_FILE, "Batch update", final_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
            st.rerun()

    # --- 履歴表示 ---
    st.divider()
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.subheader("保存済み履歴")
    with col_h2:
        if not st.session_state.journals_df.empty:
            if st.button("履歴を全削除", use_container_width=True):
                empty_df = pd.DataFrame(columns=COLUMNS)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                repo.update_file(JOURNAL_FILE, "Full reset", empty_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
                st.session_state.journals_df = empty_df
                st.rerun()

    if not st.session_state.journals_df.empty:
        th = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
        headers = ["日付", "借方", "借方額", "貸方", "貸方額", "摘要"]
        for idx, text in enumerate(headers): th[idx].caption(text)

        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
            d_amt = int(row.get('借方金額', 0))
            c_amt = int(row.get('貸方金額', 0))
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

# --- マスター確認画面（脱Excelレイアウト） ---
elif menu == "マスター確認":
    st.header("MASTER DATA")
    if not master_df.empty:
        st.caption("現在登録されている勘定科目")
        # カテゴリごとに分けて表示するなど、より見やすくする工夫
        m_cols = st.columns(3)
        for i, row in master_df.iterrows():
            with m_cols[i % 3]:
                st.markdown(f"**・ {row['勘定科目']}**")
    else:
        st.write("マスターデータが読み込めません。")

# --- 財務諸表（一時的なデータ確認） ---
elif menu == "財務諸表":
    st.header("FINANCIAL STATEMENTS")
    st.write("データ整合性確認用")
    st.dataframe(pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True))
