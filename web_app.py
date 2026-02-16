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

# 読み込み関数 (変更なし)
def load_github_csv(file_name):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(file_name)
        return pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except: return pd.DataFrame()

master_df = load_github_csv(MASTER_FILE)
account_list = master_df["勘定科目"].tolist()
journals_df = load_github_csv(JOURNAL_FILE)

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("📥 JOURNAL INPUT")
    
    # --- 修正箇所：Enterの反応を良くするため form を廃止 ---
    date = st.date_input("日付", value=datetime.now())
    col1, col2 = st.columns(2)
    with col1:
        debit = st.selectbox("借方科目 (DEBIT)", account_list)
        # 修正：value=None で初期値の0を消す。Enterで確定しやすくする
        amount = st.number_input("金額", min_value=0, step=1, value=None, placeholder="金額を入力...")
    with col2:
        credit = st.selectbox("貸方科目 (CREDIT)", account_list)
        memo = st.text_input("摘要 (MEMO)")
    
    # 登録ボタン
    submit = st.button("記帳する (REGISTER)")

    if submit:
        # 入力チェック
        if amount is None or amount <= 0:
            st.error("金額を入力してください")
        elif debit == credit:
            st.error("借方と貸方が同じ科目です")
        else:
            # GitHub保存（ここが重い原因ですが、保存の確実性を優先）
            with st.spinner("GitHubに保存中..."):
                new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                                       columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
                updated_df = pd.concat([journals_df, new_row], ignore_index=True)
                
                g = Github(GITHUB_TOKEN)
                repo = g.get_repo(REPO_NAME)
                csv_content = updated_df.to_csv(index=False)
                try:
                    contents = repo.get_contents(JOURNAL_FILE)
                    repo.update_file(JOURNAL_FILE, "Update journal", csv_content, contents.sha)
                    st.success(f"記帳完了: {amount:,} 円")
                    st.rerun() # 画面をリフレッシュして入力をクリア
                except Exception as e:
                    st.error(f"保存失敗: {e}")

    st.subheader("履歴 (HISTORY)")
    st.dataframe(journals_df.iloc[::-1], use_container_width=True)

# 他のメニュー（マスター確認、財務諸表、月次推移）は一切いじっていません。
