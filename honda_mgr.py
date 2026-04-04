import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v9.0 Final", layout="wide")

# [중요] 팀장님의 구글 시트 기반 주소 (공개 설정 필수)
SHEET_BASE = "https://docs.google.com/spreadsheets/d/1h5cEQQGrAIrrpU9qTik8PeUmpRE5zFyW2v1VVNP8e2w/edit?gid=0#gid=0"
CRM_URL = f"{SHEET_BASE}/gviz/tq?tqx=out:csv&sheet=Sheet1"
USER_URL = f"{SHEET_BASE}/gviz/tq?tqx=out:csv&sheet=Users"

# [핵심] 구글 폼 주소 (이곳에 팀장님이 만드신 구글 폼 링크를 넣으세요)
# 현재는 예시용으로 팀장님 시트 바로가기를 연결해 두었습니다.
GOOGLE_FORM_URL = SHEET_BASE 

st.markdown("""
    <style>
        .s-title { font-size: 22px !important; font-weight: bold; color: #CC0000; margin-bottom: 15px; }
        .stButton button { width: 100%; border-radius: 10px; }
        .reportview-container { background: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 로드 함수 ---
@st.cache_data(ttl=0)
def load_data(url):
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

# --- 3. 로그인 시스템 ---
user_df = load_data(USER_URL)
if not user_df.empty:
    user_db = dict(zip(user_df['ID'], user_df['Password']))
    curator_list = list(user_db.keys())
else:
    st.error("사용자 데이터를 불러올 수 없습니다. 시트의 'Users' 탭과 공개 설정을 확인하세요.")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    col1, col2 = st.columns([1, 1])
    with col1:
        input_user = st.selectbox("사용자 선택", curator_list)
        input_pw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if str(user_db.get(input_user)) == str(input_pw):
                st.session_state.logged_in = True
                st.session_state.user_name = input_user
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    st.stop()

# --- 4. 메인 화면 ---
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

# 사이드바 (필터 및 로그아웃)
selected_curator = "전체 보기"
with st.sidebar:
    st.header("⚙️ 설정")
    if st.session_state.user_name == "박스테반":
        selected_curator = st.selectbox("담당자 필터", ["전체 보기"] + curator_list)
    
    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False
        st.rerun()
    st.info("💡 데이터 수정은 아래 '시트 수정' 버튼을 이용해 주세요.")
    st.link_button("📝 구글 시트 열기", SHEET_BASE)

# 레이아웃 구성
col_reg, col_view = st.columns([1.2, 2.8])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록 / 수정</div>', unsafe_allow_html=True)
    
    # 구글 폼이나 시트를 웹페이지 안에 직접 보여주는 마법의 코드 (Iframe)
    st.write("아래 창에서 직접 데이터를 입력하거나 수정하세요.")
    st.components.v1.iframe(GOOGLE_FORM_URL, height=600, scrolling=True)

with col_view:
    st.markdown('<div class="s-title">📊 실시간 고객 명단</div>', unsafe_allow_html=True)
    
    df = load_data(CRM_URL)
    
    # 데이터 필터링 로직
    view_df = df.copy()
    if st.session_state.user_name != "박스테반":
        view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기":
        view_df = view_df[view_df['담당자'] == selected_curator]
    
    # 탭 구성
    t_all, t_con, t_del = st.tabs(["전체 명단", "계약 완료", "인도 완료"])
    
    with t_all:
        st.dataframe(view_df, use_container_width=True, height=500)
    
    with t_con:
        st.dataframe(view_df[view_df['단계'] == '계약완료'], use_container_width=True)
        
    with t_del:
        st.dataframe(view_df[view_df['단계'] == '인도완료'], use_container_width=True)

    # 새로고침 버튼
    if st.button("🔄 명단 새로고침"):
        st.cache_data.clear()
        st.rerun()
