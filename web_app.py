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

# 入力行の管理（初期値は空文字にして、選択を促す）
if 'entry_sets' not in st.session_state:
    st.session_state.entry_sets = [{"deb_s": "", "deb_a": 0, "cre_s": "", "cre_a": 0}]

master_df = load_github_csv(MASTER_FILE)
# 選択肢の先頭に空文字を追加して「未選択」状態を作れるようにする
account_list = [""] + master_df["勘定科目"].tolist() if not master_df.empty else [""]

st.sidebar.title("MENU")
menu = st.sidebar.radio("移動先", ["仕訳入力", "マスター確認", "財務諸表", "月次推移"])

if menu == "仕訳入力":
    st.header("JOURNAL INPUT")
    # 日付は一番上に一つだけ（全行共通）
    date = st.date_input("日付", value=datetime.now())

    current_entries = []
    total_deb = 0
    total_cre = 0

    for i, entry in enumerate(st.session_state.entry_sets):
        c1, c2, c3, c4 = st.columns(4)
        
        # 1行目（i=0）のみラベルを表示し、2行目以降はラベルを隠す
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
        # 追加行は勘定科目を空("")にする
        st.session_state.entry_sets.append({"deb_s": "", "deb_a": 0, "cre_s": "", "cre_a": 0})
        st.rerun()

    memo = st.text_input("摘要 (MEMO)")

    # 合計と差額の表示
    diff = total_deb - total_cre
    st.write(f"借方合計: {total_deb:,} / 貸方合計: {total_cre:,} (差額: {diff:,})")

    if st.button("リストに追加"):
        # バリデーション：合計一致かつ、何かしら入力があること
        if total_deb == total_cre and total_deb > 0:
            for entry in st.session_state.entry_sets:
                # 科目または金額が入っている行のみデータ化
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

    # --- 送信待ちエリア & 履歴表示（以前のコードを維持） ---
    st.divider()
    # (以下、以前のコードと同じため省略)
