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

# セッション状態の初期化
if 'journals_df' not in st.session_state:
    df = load_github_csv(JOURNAL_FILE)
    if not df.empty and "金額" in df.columns:
        df = df.rename(columns={"金額": "借方金額", "金額.1": "貸方金額"})
    st.session_state.journals_df = df if not df.empty else pd.DataFrame(columns=COLUMNS)

if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)

if 'entry_sets' not in st.session_state:
    st.session_state.entry_sets = [{"deb_s": "", "deb_a": 0, "cre_s": "", "cre_a": 0}]

# マスター読み込み
master_df = load_github_csv(MASTER_FILE)
account_list = [""] + (master_df["勘定科目"].tolist() if not master_df.empty else [])

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("JOURNAL INPUT")
    date = st.date_input("日付", value=datetime.now())

    # --- 仕訳入力欄 ---
    current_entries = []
    total_deb = 0
    total_cre = 0

    for i, entry in enumerate(st.session_state.entry_sets):
        c1, c2, c3, c4 = st.columns(4)
        
        # 1行目のみラベルを表示
        d_label = "借方科目" if i == 0 else ""
        da_label = "借方金額" if i == 0 else ""
        c_label = "貸方科目" if i == 0 else ""
        ca_label = "貸方金額" if i == 0 else ""

        with c1:
            d_idx = account_list.index(entry["deb_s"]) if entry["deb_s"] in account_list else 0
            deb_s = st.selectbox(d_label, account_list, index=d_idx, key=f"deb_s_{i}")
        with c2:
            deb_a = st.number_input(da_label, min_value=0, step=1, value=int(entry["deb_a"]), key=f"deb_a_{i}")
        with c3:
            c_idx = account_list.index(entry["cre_s"]) if entry["cre_s"] in account_list else 0
            cre_s = st.selectbox(c_label, account_list, index=c_idx, key=f"cre_s_{i}")
        with c4:
            cre_a = st.number_input(ca_label, min_value=0, step=1, value=int(entry["cre_a"]), key=f"cre_a_{i}")
        
        current_entries.append({"deb_s": deb_s, "deb_a": deb_a, "cre_s": cre_s, "cre_a": cre_a})
        total_deb += deb_a
        total_cre += cre_a

    st.session_state.entry_sets = current_entries

    if st.button("＋ 行を追加"):
        st.session_state.entry_sets.append({"deb_s": "", "deb_a": 0, "cre_s": "", "cre_a": 0})
        st.rerun()

    memo = st.text_input("摘要 (MEMO)")

    diff = total_deb - total_cre
    st.write(f"借方合計: {total_deb:,} / 貸方合計: {total_cre:,} (差額: {diff:,})")

    if st.button("リストに追加"):
        if total_deb == total_cre and total_deb > 0:
            for entry in st.session_state.entry_sets:
                if entry["deb_s"] != "" or entry["cre_s"] != "" or entry["deb_a"] > 0 or entry["cre_a"] > 0:
                    new_row = pd.DataFrame([[
                        date.strftime('%Y-%m-%d'), 
                        entry["deb_s"], int(entry["deb_a"]), 
                        entry["cre_s"], int(entry["cre_a"]), 
                        memo
                    ]], columns=COLUMNS)
                    st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            
            st.session_state.entry_sets = [{"deb_s": "", "deb_a": 0, "cre_s": "", "cre_a": 0}]
            st.rerun()
        else:
            st.warning("借方と貸方の合計金額を一致させてください。")

    # --- 送信待ちエリア（完全復旧） ---
    st.divider()
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1: st.subheader("送信待ちの仕訳")
    with col_t2:
        if not st.session_state.temp_journals.empty:
            if st.button("リストを全削除"):
                st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
                st.rerun()

    if not st.session_state.temp_journals.empty:
        cols_w = [1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0] 
        h = st.columns(cols_w)
        for idx, text in enumerate(["日付", "借方", "借方額", "貸方", "貸方額", "摘要"]): h[idx].caption(text)
        for i, row in st.session_state.temp_journals.iterrows():
            c = st.columns(cols_w)
            vals = [row['日付'], row['借方'], f"{int(row['借方金額']):,}", row['貸方'], f"{int(row['貸方金額']):,}", row['摘要']]
            for idx, val in enumerate(vals): c[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if c[6].button("消去", key=f"t_del_{i}"):
                st.session_state.temp_journals = st.session_state.temp_journals.drop(i).reset_index(drop=True)
                st.rerun()
        
        if st.button("GitHubへ一括保存する"):
            final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            repo.update_file(JOURNAL_FILE, "Update journal", final_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
            st.rerun()

    # --- 保存済み履歴（完全復旧） ---
    st.divider()
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1: st.subheader("保存済み履歴")
    with col_h2:
        if not st.session_state.journals_df.empty:
            if st.button("履歴を全削除"):
                empty_df = pd.DataFrame(columns=COLUMNS)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                repo.update_file(JOURNAL_FILE, "Full reset", empty_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
                st.session_state.journals_df = empty_df
                st.rerun()

    if not st.session_state.journals_df.empty:
        th = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
        for idx, text in enumerate(["日付", "借方", "借方額", "貸方", "貸方額", "摘要"]): th[idx].caption(text)
        for i, row in st.session_state.journals_df.iloc[::-1].iterrows():
            tr = st.columns([1.2, 2.0, 1.0, 2.0, 1.0, 1.8, 1.0])
            d_amt, c_amt = int(row.get('借方金額', 0)), int(row.get('貸方金額', 0))
            fields = [row['日付'], row['借方'], f"{d_amt:,}", row['貸方'], f"{c_amt:,}", row['摘要'] if pd.notna(row['摘要']) else '']
            for idx, val in enumerate(fields): tr[idx].write(f"<div class='tight-text'>{val}</div>", unsafe_allow_html=True)
            if tr[6].button("削除", key=f"h_del_{i}"):
                updated_df = st.session_state.journals_df.drop(i).reset_index(drop=True)
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                repo.update_file(JOURNAL_FILE, "Delete row", updated_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
                st.session_state.journals_df = updated_df
                st.rerun()

elif menu == "マスター確認":
    st.header("MASTER DATA")
    if not master_df.empty:
        m_cols = st.columns(3)
        for i, row in master_df.iterrows():
            with m_cols[i % 3]:
                with st.expander(f"{row['勘定科目']}"):
                    st.markdown(f"<div style='font-size: 0.85rem;'>■分類: {row['分類']}<br>■詳細: {row['詳細分類']}<br>■方向: {row['計算方向']}<br>■コード: {row['コード(参考)']}</div>", unsafe_allow_html=True)
