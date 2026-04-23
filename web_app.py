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
        df = df.rename(columns={"金額": "借方金額", "金額.1": "貸方金額"})
    st.session_state.journals_df = df if not df.empty else pd.DataFrame(columns=COLUMNS)

if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)

# 【追加】複数行仕訳の作業用バッファ
if 'multi_buffer' not in st.session_state:
    st.session_state.multi_buffer = pd.DataFrame(columns=COLUMNS)

master_df = load_github_csv(MASTER_FILE)
account_list = master_df["勘定科目"].tolist() if not master_df.empty else []

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("JOURNAL INPUT")
    
    # モード選択
    input_mode = st.radio("入力モード", ["通常入力", "複数行入力"], horizontal=True)
    
    date = st.date_input("日付", value=datetime.now())
    memo = st.text_input("摘要 (MEMO)")

    if input_mode == "通常入力":
        c1, c2, c3, c4 = st.columns(4)
        with c1: deb_sub = st.selectbox("借方科目", account_list, key="deb_s")
        with c2: deb_amt = st.number_input("借方金額", min_value=0, step=1, key="deb_a")
        with c3: cre_sub = st.selectbox("貸方科目", account_list, key="cre_s")
        with c4: cre_amt = st.number_input("貸方金額", min_value=0, step=1, key="cre_a")

        if st.button("リストに追加"):
            if deb_amt > 0 or cre_amt > 0:
                new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), deb_sub, int(deb_amt), cre_sub, int(cre_amt), memo]], columns=COLUMNS)
                st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
                st.rerun()

    else:
        # --- 複数行入力エリア ---
        st.info("借方と貸方の合計金額を一致させてください。")
        mc1, mc2, mc3 = st.columns([2, 1, 1])
        with mc1: m_sub = st.selectbox("科目選択", account_list, key="m_sub")
        with mc2: m_side = st.radio("貸借", ["借方", "貸方"], horizontal=True)
        with mc3: m_amt = st.number_input("金額", min_value=0, step=1, key="m_amt")

        if st.button("行を追加"):
            d_val = m_amt if m_side == "借方" else 0
            c_val = m_amt if m_side == "貸方" else 0
            d_sub = m_sub if m_side == "借方" else ""
            c_sub = m_sub if m_side == "貸方" else ""
            
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), d_sub, int(d_val), c_sub, int(c_val), memo]], columns=COLUMNS)
            st.session_state.multi_buffer = pd.concat([st.session_state.multi_buffer, new_row], ignore_index=True)
            st.rerun()

        # 作業中リストの表示
        if not st.session_state.multi_buffer.empty:
            st.write("--- 作業中の仕訳 ---")
            for idx, row in st.session_state.multi_buffer.iterrows():
                bc = st.columns([3, 1, 1, 1])
                bc[0].write(row['借方'] if row['借方'] else row['貸方'])
                bc[1].write(f"借: {int(row['借方金額']):,}")
                bc[2].write(f"貸: {int(row['貸方金額']):,}")
                if bc[3].button("削除", key=f"buf_del_{idx}"):
                    st.session_state.multi_buffer = st.session_state.multi_buffer.drop(idx).reset_index(drop=True)
                    st.rerun()

            deb_total = st.session_state.multi_buffer["借方金額"].sum()
            cre_total = st.session_state.multi_buffer["貸方金額"].sum()
            diff = deb_total - cre_total
            
            st.markdown(f"**借方合計: {deb_total:,} / 貸方合計: {cre_total:,} (差額: {diff:,})**")
            
            if st.button("この仕訳を確定してリストへ", disabled=(deb_total != cre_total or deb_total == 0)):
                st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, st.session_state.multi_buffer], ignore_index=True)
                st.session_state.multi_buffer = pd.DataFrame(columns=COLUMNS)
                st.rerun()
            if st.button("クリア"):
                st.session_state.multi_buffer = pd.DataFrame(columns=COLUMNS)
                st.rerun()

    # --- 送信待ちエリア ---
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
            repo.update_file(JOURNAL_FILE, "Add multi-row journal", final_df.to_csv(index=False), repo.get_contents(JOURNAL_FILE).sha)
            st.session_state.journals_df = final_df
            st.session_state.temp_journals = pd.DataFrame(columns=COLUMNS)
            st.rerun()

    # --- 保存済み履歴（変更なし） ---
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

# マスター確認画面（変更なし）
elif menu == "マスター確認":
    st.header("MASTER DATA")
    if not master_df.empty:
        m_cols = st.columns(3)
        for i, row in master_df.iterrows():
            with m_cols[i % 3]:
                with st.expander(f"{row['勘定科目']}"):
                    st.markdown(f"<div style='font-size: 0.85rem;'>■分類: {row['分類']}<br>■詳細: {row['詳細分類']}<br>■方向: {row['計算方向']}<br>■コード: {row['コード(参考)']}</div>", unsafe_allow_html=True)
