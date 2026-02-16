import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- ページ設定 & デザイン (変更なし) ---
st.set_page_config(page_title="P5 Style Accounting", layout="wide")
st.markdown("""<style>.main { background-color: #000; color: #FFF; } .stButton>button { background-color: #F00; color: white; }</style>""", unsafe_allow_html=True)

# --- 設定 & GitHub接続 ---
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

master_df = load_github_csv(MASTER_FILE)
account_list = master_df["勘定科目"].tolist()
master_dict = master_df.set_index("勘定科目").to_dict(orient="index")
journals_df = load_github_csv(JOURNAL_FILE)

# --- サイドナビゲーション ---
st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("📥 JOURNAL INPUT")
    
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("日付", value=datetime.now())
        col1, col2 = st.columns(2)
        with col1:
            debit = st.selectbox("借方科目 (DEBIT)", account_list)
            # keyを設定して、入力値を確実に取得
            amount = st.number_input("金額", min_value=0, step=1, key="input_amount")
        with col2:
            credit = st.selectbox("貸方科目 (CREDIT)", account_list)
            memo = st.text_input("摘要 (MEMO)")
        
        submit = st.form_submit_button("記帳する (REGISTER)")

    # --- ここが修正したロジックです ---
    if submit:
        # 入力チェック：金額が0円、または借借が同じ場合は保存しない
        if amount <= 0:
            st.error("金額が入力されていません（0円は登録できません）")
        elif debit == credit:
            st.error("借方と貸方が同じ科目です")
        else:
            # GitHub保存
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                                   columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
            updated_df = pd.concat([journals_df, new_row], ignore_index=True)
            
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            csv_content = updated_df.to_csv(index=False)
            try:
                contents = repo.get_contents(JOURNAL_FILE)
                repo.update_file(JOURNAL_FILE, "Update journal", csv_content, contents.sha)
                st.success(f"{amount:,} 円 記帳成功！")
                st.rerun()
            except Exception as e:
                st.error(f"保存失敗: {e}")

    st.subheader("履歴 (HISTORY)")
    st.dataframe(journals_df.iloc[::-1], use_container_width=True)

# 財務諸表、月次推移、マスター確認のコードは「いじらないで」とのことですので、
# 前回のロジックをそのまま維持してください（省略しますが、変更は加えていません）。
