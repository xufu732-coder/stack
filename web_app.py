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

# --- データの読み込み ---
def load_github_csv(file_name):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(file_name)
        return pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except: return pd.DataFrame()

# アプリ起動時に一度だけ読み込み
if 'master_df' not in st.session_state:
    st.session_state.master_df = load_github_csv(MASTER_FILE)
if 'journals_df' not in st.session_state:
    st.session_state.journals_df = load_github_csv(JOURNAL_FILE)

# 【新規】アプリ内に一時的に溜めておくリスト
if 'temp_journals' not in st.session_state:
    st.session_state.temp_journals = pd.DataFrame(columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])

account_list = st.session_state.master_df["勘定科目"].tolist()

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("📥 JOURNAL INPUT (サクサク入力モード)")
    
    # --- 入力エリア ---
    date = st.date_input("日付", value=datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        debit = st.selectbox("借方科目 (DEBIT)", account_list)
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="金額入力後Enter")
    with col2:
        credit = st.selectbox("貸方科目 (CREDIT)", account_list)
        memo = st.text_input("摘要 (MEMO)")
    
    # --- 仮登録ロジック (Enter/ボタンで即反応) ---
    if st.button("リストに追加 (Add to list)"):
        if amount and amount > 0 and debit != credit:
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                                   columns=st.session_state.temp_journals.columns)
            # session_state(メモリ)に追加するだけなので一瞬で終わります
            st.session_state.temp_journals = pd.concat([st.session_state.temp_journals, new_row], ignore_index=True)
            st.rerun()
        else:
            st.error("入力内容を確認してください（金額0や、借貸が同じ科目は不可）")

    # --- 一時保存リストの表示 ---
    st.subheader("📝 送信待ちの仕訳 (未保存)")
    if not st.session_state.temp_journals.empty:
        st.table(st.session_state.temp_journals)
        
        # --- ここで一括保存 ---
        if st.button("🚀 GitHubへ一括保存する (Save all to GitHub)"):
            with st.spinner("通信中..."):
                # 既存のデータと合体
                final_df = pd.concat([st.session_state.journals_df, st.session_state.temp_journals], ignore_index=True)
                
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                csv_content = final_df.to_csv(index=False)
                try:
                    contents = repo.get_contents(JOURNAL_FILE)
                    repo.update_file(JOURNAL_FILE, "Batch update journal", csv_content, contents.sha)
                    
                    # 成功したらメモリを空にして本番データを更新
                    st.session_state.journals_df = final_df
                    st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
                    st.success("GitHubへの一括保存が完了しました！")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失敗: {e}")
        
        if st.button("リストをクリア"):
            st.session_state.temp_journals = pd.DataFrame(columns=st.session_state.temp_journals.columns)
            st.rerun()
    else:
        st.info("上にデータを入力してEnterを押すと、ここに溜まっていきます。")

    st.divider()
    st.subheader("📖 保存済み履歴 (HISTORY)")
    st.dataframe(st.session_state.journals_df.iloc[::-1], use_container_width=True)

# 財務諸表、月次推移、マスター確認はいじっていません

