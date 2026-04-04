import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io

# --- [필수 설정] 공개된 구글 시트 주소 ---
# 팀장님 시트 ID를 기반으로 CSV 추출 주소를 생성했습니다.
SHEET_BASE = "https://docs.google.com/spreadsheets/d/1h5cEQQGrAIrrpU9qTik8PeUmpRE5zFyW2v1VVNP8e2w"
CRM_URL = f"{SHEET_BASE}/gviz/tq?tqx=out:csv&sheet=Sheet1"
USER_URL = f"{SHEET_BASE}/gviz/tq?tqx=out:csv&sheet=Users"

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v8.0 Final", layout="wide")

st.markdown("""
    <style>
        .s-title { white-space: nowrap; font-size: 21px !important; font-weight: bold; margin-bottom: 15px; }
        .stButton button { width: 100%; }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 18px; font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 로드 함수 (열쇠 없이 바로 읽기) ---
@st.cache_data(ttl="0s")
def load_crm_data():
    return pd.read_csv(CRM_URL)

@st.cache_data(ttl="0s")
def load_user_data():
    return pd.read_csv(USER_URL)

# [참고] 쓰기 기능은 공개 시트에서 직접 쓰기가 제한될 수 있어, 
# 가장 확실한 방법은 팀장님이 시트에서 직접 관리하시거나 AppSheet를 병행하는 것이지만
# 일단 기존 화면 UI는 모두 그대로 유지해 드립니다.
def save_data_dummy(df):
    st.info("💡 데이터 저장/수정은 현재 '읽기 전용' 모드입니다. 실제 데이터 반영은 구글 시트나 앱시트를 이용해 주세요!")

# --- 3. 로그인 시스템 ---
try:
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'], user_df['Password']))
    curator_list = list(user_db.keys())
except Exception as e:
    st.error(f"⚠️ 사용자 데이터를 불러올 수 없습니다: {e}")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    input_user = st.selectbox("사용자 선택", curator_list)
    input_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(input_user) == str(input_pw):
            st.session_state.logged_in = True
            st.session_state.user_name = input_user
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_crm_data()

# --- 5. 사이드바 ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user_name} 팀장님")
    with st.expander("🔐 비밀번호 변경"):
        st.info("비밀번호 변경은 구글 시트의 'Users' 탭에서 직접 수정해 주세요.")
    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

st.title("🚗 Honda 통합 고객 관리 시스템")

# --- 6. 팀장 관리 도구 (박스테반 전용) ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구"):
        m_tab1, m_tab2 = st.tabs(["🔍 담당자 필터", "🔄 인계/인사 안내"])
        with m_tab1:
            selected_curator = st.selectbox("조회할 담당자 선택", ["전체 보기"] + curator_list)
        with m_tab2:
            st.write("인사 및 인계 작업은 구글 시트에서 행을 수정/삭제하여 관리해 주세요.")

st.divider()

# --- 7. 메인 화면 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 등록 (안내)</div>', unsafe_allow_html=True)
    st.write("현재 버전은 실시간 조회 전용입니다. 신규 고객은 구글 시트에 직접 입력해 주세요.")
    with st.form("reg_form"):
        st.text_input("고객명")
        st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        st.form_submit_button("저장 (읽기전용)")

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체", "📝 계약", "🚚 인도", "🚫 취소"])
    
    view_df = df.copy()
    if st.session_state.user_name != "박스테반":
        view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기":
        view_df = view_df[view_df['담당자'] == selected_curator]

    def display_list(target_df, prefix):
        if target_df.empty:
            st.write("표시할 고객이 없습니다.")
            return
        for idx, row in target_df.iterrows():
            with st.expander(f"📌 [{row['단계']}] {row['고객명']} ({row['모델']}) - {row['담당자']}"):
                st.write(f"**기준일:** {row['기준일']}")
                st.write(f"**비고:** {row['비고']}")
                if row['단계'] == "인도완료":
                    st.write("--- 사후 관리 일정 ---")
                    try:
                        base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                        st.write(f"1개월: {(base_d + relativedelta(months=1)).strftime('%Y-%m-%d')}")
                        st.write(f"3개월: {(base_d + relativedelta(months=3)).strftime('%Y-%m-%d')}")
                    except: pass

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == '계약완료'], "con")
    with t_del: display_list(view_df[view_df['단계'] == '인도완료'], "del")
    with t_can: display_list(view_df[view_df['단계'] == '계약취소'], "can")
