import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v23.0 Final", layout="wide")

# --- 2. 데이터 연결 및 자동 보정 로직 ---
@st.cache_resource
def get_connection():
    try:
        # Secrets에서 데이터를 가져와 줄바꿈 기호를 수동으로 보정합니다.
        # st.secrets는 읽기 전용이므로 내부 딕셔너리 구조를 활용합니다.
        conf = st.secrets.connections.gsheets.to_dict()
        
        # 줄바꿈(\n)이 포함된 비밀키를 기계가 읽기 쉬운 형식으로 강제 변환
        if "private_key" in conf:
            raw_key = conf["private_key"]
            # 실제 엔터(줄바꿈)를 문자열 '\n'으로 치환
            conf["private_key"] = raw_key.replace("\n", "\\n")
            
        # 보정된 설정으로 연결 시도
        return st.connection("gsheets", type=GSheetsConnection, **conf)
    except Exception as e:
        st.error(f"🚨 연결 설정 중 오류: {e}")
        return None

try:
    conn = get_connection()
    
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)

    # 구글 시트에서 사용자 목록 불러오기
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error("🚨 구글 시트 연결 실패! 아래 내용을 꼭 확인해주세요.")
    st.warning(f"🔍 에러 원인: {e}")
    st.info("💡 해결 방법: 1. 시트 공유(편집자 권한) 2. 탭 이름(Sheet1, Users) 3. 시트 1행 제목(ID, Password)")
    st.stop()

# --- 3. 로그인 시스템 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    if not curator_list:
        st.error("사용자 정보가 시트에 없습니다. 'Users' 탭을 확인하세요.")
    else:
        u = st.selectbox("사용자 선택", curator_list)
        p = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if user_db.get(u) == p:
                st.session_state.logged_in = True
                st.session_state.user_name = u
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    st.stop()

# --- 4. 메인 화면 ---
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

# 사이드바
if st.sidebar.button("🚪 로그아웃"):
    st.session_state.logged_in = False; st.rerun()

# [신규 고객 등록]
with st.expander("➕ 신규 고객 등록", expanded=False):
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("시트에 저장"):
            if name:
                new_id = 1 if df.empty or 'ID' not in df.columns else int(df['ID'].max()) + 1
                new_row = {
                    "ID": new_id, "고객명": name, "담당자": st.session_state.user_name,
                    "기준일": str(datetime.now().date()), "모델": mdl, "단계": "계약완료", "비고": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_crm_data(df); st.success(f"✅ {name}님 등록 완료!"); st.rerun()

# [고객 리스트 및 상태 관리]
st.subheader("📊 고객 관리 현황")

# 팀장님은 전체, 팀원은 본인 데이터만 필터링
view_df = df.copy()
if st.session_state.user_name != "박스테반":
    view_df = view_df[view_df['담당자'] == st.session_state.user_name]

st.dataframe(view_df, use_container_width=True)

# 인도 완료 처리 기능
con_df = view_df[view_df['단계'] == "계약완료"]
if not con_df.empty:
    with st.expander("🚚 인도 처리 대기 목록"):
        for idx, row in con_df.iterrows():
            if st.button(f"인도 완료: {row['고객명']} ({row['모델']})", key=f"btn_{row['ID']}"):
                df.loc[df['ID'] == row['ID'], '단계'] = "인도완료"
                save_crm_data(df); st.rerun()
