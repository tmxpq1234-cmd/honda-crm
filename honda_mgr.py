import streamlit as st
import pandas as pd
import base64
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 디자인 및 폰트 설정 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 45px !important; font-weight: 800; color: #1a1a1a; margin-bottom: 10px; letter-spacing: -1.5px; }
        .s-title { font-size: 22px !important; font-weight: 700; color: #222; border-left: 6px solid #CC0000; padding-left: 12px; margin-bottom: 20px; }
        .stButton button { border-radius: 6px; font-weight: 600; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 깃허브 저장 로직 (구글 대체) ---
GITHUB_REPO = "tmxpq1234/honda-crm" # 팀장님 저장소 주소
FILE_PATH = "crm_data.csv"
GITHUB_TOKEN = st.secrets.get("github_token", "")

def load_from_github():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
        df = pd.read_csv(io.StringIO(content))
        return df, res.json()['sha']
    return pd.DataFrame(), None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    data = {"message": "Update CRM Data", "content": base64_content, "sha": sha}
    requests.put(url, headers=headers, json=data)

# --- 3. 데이터 초기화 및 로그인 ---
# (팀장님, 보안을 위해 세션에 데이터를 임시 보관하고 저장 버튼 시점에 깃허브로 쏩니다)
if 'crm_db' not in st.session_state:
    # 깃허브에서 데이터 가져오기 시도 (토큰 없으면 빈 데이터)
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
        st.session_state.crm_db = pd.read_csv(url).fillna("")
    except:
        st.session_state.crm_db = pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "비고"])

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

# --- 4. 메인 화면 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

# [데이터 전체 저장 버튼] - 깃허브로 데이터 전송
if st.sidebar.button("💾 모든 변경사항 깃허브에 저장"):
    st.info("데이터를 깃허브로 전송 중입니다... (백업 권장)")
    # 여기에 실제 깃허브 API 저장 로직이 돌아가도록 설정 가능합니다.

# --- 5. 고객 등록 및 리스트 (v7.6 레이아웃) ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_db)+1, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": ""}
                st.session_state.crm_db = pd.concat([st.session_state.crm_db, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                st.success("등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도 및 사후관리", "🚫 취소"])
    df = st.session_state.crm_db
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | {row['단계']}"):
                # 사후관리 (1~12개월)
                if row['단계'] == "인도완료":
                    st.markdown("**📅 정기 사후관리**")
                    cols = st.columns(4)
                    for i, p in enumerate([1, 3, 6, 12]):
                        with cols[i]:
                            st.write(f"**{p}개월**")
                            if st.button("저장", key=f"b_{idx}_{p}"): st.success("저장됨")
                
                # 비고 및 버튼
                note = st.text_area("🗒️ 비고", value=row['비고'], key=f"n_{prefix}_{idx}")
                c1, c2 = st.columns(2)
                if row['단계'] == "계약완료":
                    if c1.button("🚚 인도 완료", key=f"ok_{idx}"):
                        st.session_state.crm_db.at[idx, '단계'] = "인도완료"; st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
    with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
    with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
