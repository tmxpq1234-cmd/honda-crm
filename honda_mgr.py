import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v24.0 Final", layout="wide")

# --- 2. 데이터 연결 (충돌 해결 버전) ---
@st.cache_resource
def get_connection():
    try:
        # Secrets 내용을 가져옵니다.
        conf = st.secrets.connections.gsheets.to_dict()
        
        # 비밀키 내의 실제 줄바꿈(\n) 보정
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\n", "\\n")
            
        # 💡 [해결 포인트] connection 함수에 중복된 type 인자를 주지 않고 
        # conf(Secrets 내용)만 통째로 던져줍니다.
        return st.connection("gsheets", **conf) 
    except Exception as e:
        st.error(f"🚨 연결 설정 중 오류: {e}")
        return None

try:
    conn = get_connection()
    if conn is None:
        st.stop()
        
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)

    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error("🚨 구글 시트 연결 실패!")
    st.warning(f"🔍 에러 원인: {e}")
    st.info("💡 해결 방법: 1. 시트 공유(편집자) 2. 탭 이름(Sheet1, Users) 3. 1행 제목(ID, Password)")
    st.stop()

# --- 3. 로그인 및 메인 로직 (기존과 동일) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    u = st.selectbox("사용자 선택", curator_list if curator_list else ["데이터 없음"])
    p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True
            st.session_state.user_name = u
            st.rerun()
        else: st.error("비밀번호 오류")
    st.stop()

# [메인 관리 화면]
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

with st.expander("➕ 신규 고객 등록"):
    with st.form("reg"):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V", "PILOT", "ODYSSEY"])
        if st.form_submit_button("저장"):
            if name:
                new_id = 1 if df.empty else int(df['ID'].max()) + 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": "계약완료", "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_crm_data(df); st.success("등록 완료!"); st.rerun()

st.dataframe(df, use_container_width=True)
