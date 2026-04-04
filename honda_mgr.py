import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v20.0 Final", layout="wide")

# --- 2. 데이터 연결 및 에러 처리 ---
try:
    # 💡 [핵심] Secrets의 줄바꿈 문제를 코드에서 강제로 해결합니다.
    if "connections" in st.secrets and "gsheets" in st.secrets.connections:
        # 비밀키에 포함된 실제 줄바꿈을 기계가 읽는 \n 문자로 변환
        raw_key = st.secrets.connections.gsheets.private_key
        if "-----BEGIN PRIVATE KEY-----" in raw_key:
            clean_key = raw_key.replace("\n", "\\n")
            # 다시 설정 (메모리상에서만 수정됨)
            st.secrets.connections.gsheets.private_key = clean_key

    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)

    user_df = load_user_data()
    # Users 시트의 ID, Password 컬럼을 읽어 로그인 DB 생성
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error("🚨 데이터 연결 실패! 아래 내용을 확인해주세요.")
    st.warning(f"🔍 상세 에러: {e}")
    st.info("💡 해결 방법: 1. 시트 공유 설정(편집자), 2. 시트 탭 이름(Sheet1, Users), 3. Secrets 주소 확인")
    st.stop()

# --- 3. 로그인 시스템 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    u = st.selectbox("사용자 선택", curator_list)
    p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True
            st.session_state.user_name = u
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 4. 메인 화면 ---
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

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

# [고객 리스트]
st.subheader("📊 현황 리스트")
st.dataframe(df, use_container_width=True)
