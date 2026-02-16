import streamlit as st
import pandas as pd
from github import Github
from datetime import datetime
import io

# --- ページ設定 & デザイン ---
st.set_page_config(page_title="P5 Style Accounting", layout="wide")

# CSSでデザインをP5風（黒・赤・白）に強制変更
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .stButton>button { background-color: #FF0000; color: white; border-radius: 0px; border: none; width: 100%; }
    .stDataFrame { border: 1px solid #FF0000; }
    h1, h2, h3 { color: #FF0000 !important; font-family: 'MS Gothic'; }
    div[data-baseweb="select"] > div { background-color: #111; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 設定 & GitHub接続 ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_NAME = "xufu732-coder/stack" 
JOURNAL_FILE = "journal.csv"
MASTER_FILE = "categories.csv" # 以前の master_df に相当

# GitHubからデータを読み込む関数
def load_github_csv(file_name):
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(file_name)
        return pd.read_csv(io.StringIO(contents.decoded_content.decode('utf-8')))
    except:
        return pd.DataFrame()

# --- 1. マスター読み込み ---
master_df = load_github_csv(MASTER_FILE)
if master_df.empty:
    st.error("マスターファイル(categories.csv)が見つかりません。")
    st.stop()

# 勘定科目リストと辞書の作成（以前の self.master_data に相当）
account_list = master_df["勘定科目"].tolist()
master_dict = master_df.set_index("勘定科目").to_dict(orient="index")

# --- 2. 仕訳データの読み込み ---
journals_df = load_github_csv(JOURNAL_FILE)

# --- サイドナビゲーション ---
st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

# --- A. 仕訳入力ページ ---
if menu == "仕訳入力":
    st.header("📥 JOURNAL INPUT")
    
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("日付", value=datetime.now())
        col1, col2 = st.columns(2)
        with col1:
            debit = st.selectbox("借方科目 (DEBIT)", account_list)
            amount = st.number_input("金額", min_value=0, step=1000)
        with col2:
            credit = st.selectbox("貸方科目 (CREDIT)", account_list)
            memo = st.text_input("摘要 (MEMO)")
        
        submit = st.form_submit_button("記帳する (REGISTER)")

    if submit:
        # GitHub保存ロジック（以前の register_journal に相当）
        new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), debit, amount, credit, amount, memo]], 
                               columns=["日付", "借方", "金額", "貸方", "金額.1", "摘要"])
        updated_df = pd.concat([journals_df, new_row], ignore_index=True)
        
        # GitHubへプッシュ
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = updated_df.to_csv(index=False)
        try:
            contents = repo.get_contents(JOURNAL_FILE)
            repo.update_file(JOURNAL_FILE, "Update journal", csv_content, contents.sha)
        except:
            repo.create_file(JOURNAL_FILE, "Create journal", csv_content)
        
        st.success("GitHubへの保存に成功！")
        st.rerun()

    st.subheader("履歴 (HISTORY)")
    st.dataframe(journals_df.iloc[::-1], use_container_width=True) # 逆順表示

# --- B. マスター確認ページ ---
elif menu == "マスター確認":
    st.header("🗂 MASTER CHECK")
    st.table(master_df)

# --- C. 財務諸表ページ (P/L, B/S) ---
elif menu == "財務諸表":
    st.header("📊 FINANCIAL STATEMENTS")
    
    if journals_df.empty:
        st.warning("仕訳データがありません。")
    else:
        # 残高計算ロジック（以前の update_all_reports を移植）
        balances = {name: 0 for name in account_list}
        for _, j in journals_df.iterrows():
            d, c, a = j['借方'], j['貸方'], j['金額']
            if d in master_dict:
                balances[d] += a if master_dict[d]['分類'] in ["資産", "費用"] else -a
            if c in master_dict:
                balances[c] += a if master_dict[c]['分類'] in ["負債", "純資産", "収益"] else -a
        
        tab1, tab2 = st.tabs(["損益計算書 (P/L)", "貸借対照表 (B/S)"])
        
        with tab1:
            # P/L報告式の簡易再現
            def get_sum(detail_type):
                return sum(balances[acc] * master_dict[acc]['計算方向'] 
                           for acc in balances if acc in master_dict and master_dict[acc]['詳細分類'] == detail_type)
            
            s = get_sum("売上高"); c = get_sum("売上原価"); gp = s - c
            sg = get_sum("販売費及び一般管理費"); op = gp - sg
            st.metric("売上高", f"{s:,} 円")
            st.metric("売上総利益", f"{gp:,} 円")
            st.metric("営業利益", f"{op:,} 円", delta=f"{op:,}")

        with tab2:
            # B/Sの簡易表示
            bs_data = [{"科目": k, "金額": v} for k, v in balances.items() if v != 0]
            st.table(pd.DataFrame(bs_data))

# --- D. 月次推移ページ ---
elif menu == "月次推移":
    st.header("📈 MONTHLY TREND")
    if not journals_df.empty:
        journals_df['年月'] = journals_df['日付'].str[:7]
        monthly_summary = journals_df.groupby(['年月', '借方'])['金額'].sum().unstack(fill_value=0)
        st.line_chart(monthly_summary)
    else:
        st.info("データがありません。")
