import streamlit as st
import pandas as pd
from github import Github # 最初にエラーが出るかもしれませんが、後で直せます
from datetime import datetime
import io

st.title("📝 鉄壁の保存機能付き・会計アプリ")

# --- 設定（ここを自分の情報に変えるだけ） ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"] # 後で設定します
REPO_NAME = "xufu732-coder/stack" # あなたのリポジトリ名
FILE_PATH = "journal.csv" # 保存するファイル名

# --- 1. 勘定科目の読み込み ---
try:
    category_list = pd.read_csv('categories.csv')['勘定科目'].tolist()
except:
    category_list = ["現金", "普通預金"]

# --- 2. 保存ボタンが押された時の処理 ---
with st.form("input_form"):
    date = st.date_input("日付")
    debit = st.selectbox("借方", category_list)
    credit = st.selectbox("貸方", category_list)
    amount = st.number_input("金額", min_value=0)
    memo = st.text_input("摘要")
    submit = st.form_submit_button("GitHubに保存する")

if submit:
    try:
        # GitHubに接続
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # 現在のCSVを取得、なければ新規作成
        try:
            contents = repo.get_contents(FILE_PATH)
            df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
        except:
            df = pd.DataFrame(columns=["日付", "借方", "貸方", "金額", "摘要"])

        # 新しいデータを追加
        new_row = pd.DataFrame([[date, debit, credit, amount, memo]], columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        
        # CSVを文字列に戻してGitHubへ送る
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        if 'contents' in locals():
            repo.update_file(FILE_PATH, "Update journal", csv_buffer.getvalue(), contents.sha)
        else:
            repo.create_file(FILE_PATH, "Create journal", csv_buffer.getvalue())
            
        st.success("GitHubへの保存に成功しました！これで絶対に消えません。")
        st.balloons()
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# --- 3. 現在のデータ表示 ---
st.header("📖 記帳済みのデータ")
try:
    # 常にGitHubから最新を読み込む
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    contents = repo.get_contents(FILE_PATH)
    current_df = pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    st.table(current_df)
except:
    st.info("まだ保存されたデータはありません。")
