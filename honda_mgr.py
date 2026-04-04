import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (팀장님 정보로 확인 완료) ---
GITHUB_REPO = "tmxpq1234/honda-crm"
FILE_PATH = "crm_data.csv"
# Secrets에 github_token이 등록되어 있어야 실시간 저장이 됩니다.
GITHUB_TOKEN = st.secrets.get("github_token", "")

# --- 2. 디자인 설정 (타이틀 확대 및 서체) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 45px !important; font-weight: 800; color: #1a1a1a; margin-bottom: 10px; }
        .s-title { font-size: 22px !important; font-weight: 700; color: #222; border-left: 6px solid #CC0000; padding-left: 12px; margin-bottom: 20px; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 데이터 로드/저장 함수 (GitHub API 활용) ---
def load_data():
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
            return pd.read_csv(io.StringIO(content)).fillna(""), res.json()['sha']
    except: pass
    return pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "비고"]), None

def save_data(df, sha):
    if not GITHUB_TOKEN: 
        st.warning("⚠️ GitHub Token이 없어 파일에 직접 저장되지 않습니다. Secrets 설정을 확인하세요.")
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    payload = {"message": f"Update {datetime.now()}", "content": base64_content, "sha": sha}
    requests.put(url, headers=headers, json=payload)

# --- 4. 로그인 시스템 ---
USER_DB = {"박스테반": "1234", "김태형": "2290", "전유인": "2290", "전명현": "2290", "이준창": "2290"}
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">🔐 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER ID", list(USER_DB.keys()))
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if USER_DB.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# 데이터 로드
if 'crm_df' not in st.session_state or st.sidebar.button("🔄 시트 새로고침"):
    df, sha = load_data()
    st.session_state.crm_df, st.session_state.file_sha = df, sha

# --- 5. 메인 레이아웃 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

with st.sidebar:
    st.write(f"**접속자: {st.session_state.user_name}**")
    if st.button("🚪 LOGOUT"): st.session_state.logged_in = False; st.rerun()

# [등록 및 리스트]
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": ""}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_data(st.session_state.crm_df, st.session_state.file_sha); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도 및 사후관리", "🚫 취소"])
    df = st.session_state.crm_df
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            # 💡 [해결!] prefix를 활용해 버튼 ID 중복을 원천 차단했습니다.
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | {row['단계']}"):
                note = st.text_area("🗒️ 비고", value=row['비고'], key=f"n_{prefix}_{idx}")
                if st.button("비고 저장", key=f"nb_{prefix}_{idx}"):
                    st.session_state.crm_df.at[idx, '비고'] = note
                    save_data(st.session_state.crm_df, st.session_state.file_sha); st.rerun()

                if row['단계'] == "계약완료":
                    c1, c2 = st.columns(2)
                    if c1.button("🚚 인도 완료 처리", key=f"ok_{prefix}_{idx}"):
                        st.session_state.crm_df.at[idx, '단계'] = "인도완료"
                        st.session_state.crm_df.at[idx, '기준일'] = str(datetime.now().date())
                        save_data(st.session_state.crm_df, st.session_state.file_sha); st.rerun()
                    if c2.button("🚫 취소 처리", key=f"can_{prefix}_{idx}"):
                        st.session_state.crm_df.at[idx, '단계'] = "계약취소"
                        save_data(st.session_state.crm_df, st.session_state.file_sha); st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
    with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
    with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
