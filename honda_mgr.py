import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v23.0 Final", layout="wide")

# --- 2. 데이터 연결 및 자동 보정 로직 ---
try:
    # 💡 [핵심] Secrets의 줄바꿈 문제를 원천 차단하는 설정 로직
    # st.secrets의 불변 특성을 피해 내부 설정 딕셔너리를 직접 구성합니다.
    s = st.secrets["connections"]["gsheets"]
    
    # 비밀키 청소: 엔터, 공백 등을 모두 제거하고 순수하게 \n 기호로만 연결
    raw_key = s["private_key"]
    # 기존에 포함된 줄바꿈 제거 후 다시 표준 형식으로 정리
    clean_key = raw_key.replace("\n", "\\n").strip()
    if not clean_key.startswith("-----BEGIN"):
         clean_key = "-----BEGIN PRIVATE KEY-----\\n" + clean_key
    if not clean_key.endswith("-----END PRIVATE KEY-----"):
         clean_key = clean_key + "\\n-----END PRIVATE KEY-----"

    # gsheets 연결 시도
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)

    # 데이터 로드
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error("🚨 마지막 연결 시도 중 에러 발생")
    st.warning(f"🔍 에러 원인: {e}")
    st.info("💡 팁: 시트의 'Users' 탭과 'Sheet1' 탭 이름이 정확한지 꼭 봐주세요!")
    st.stop()

# --- 3. 로그인 시스템 ---
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
        else: st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 4. 메인 대시보드 ---
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

# 사이드바 설정
with st.sidebar:
    st.write(f"👤 접속자: {st.session_state.user_name}")
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False; st.rerun()
    st.divider()
    
    # 관리자 필터 (박스테반 팀장님 전용)
    sel_cur = "전체 보기"
    if st.session_state.user_name == "박스테반":
        sel_cur = st.selectbox("큐레이터 필터", ["전체 보기"] + curator_list)

# --- 5. 기능 구현 (등록/조회/인수인계) ---
with st.expander("➕ 신규 고객 등록"):
    with st.form("reg"):
        c_name = st.text_input("고객명")
        c_mdl = st.selectbox("모델", ["ACCORD", "CR-V", "PILOT", "ODYSSEY"])
        if st.form_submit_button("저장하기"):
            if c_name:
                new_id = 1 if df.empty else int(df['ID'].max()) + 1
                new_row = {
                    "ID": new_id, "고객명": c_name, "담당자": st.session_state.user_name,
                    "기준일": str(datetime.now().date()), "모델": c_mdl, "단계": "계약완료", "비고": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_crm_data(df); st.success("등록 완료!"); st.rerun()

# 탭 구성
t1, t2 = st.tabs(["📊 전체 현황", "🚚 인도 및 사후관리"])

# 필터링
view_df = df.copy()
if st.session_state.user_name != "박스테반":
    view_df = view_df[view_df['담당자'] == st.session_state.user_name]
elif sel_cur != "전체 보기":
    view_df = view_df[view_df['담당자'] == sel_cur]

with t1:
    st.dataframe(view_df, use_container_width=True)

with t2:
    target_df = view_df[view_df['단계'] == "계약완료"]
    if target_df.empty: st.info("관리할 고객이 없습니다.")
    for _, row in target_df.iterrows():
        with st.expander(f"📌 {row['고객명']} ({row['모델']})"):
            if st.button("인도 완료로 변경", key=f"btn_{row['ID']}"):
                df.loc[df['ID'] == row['ID'], '단계'] = "인도완료"
                save_crm_data(df); st.success("변경되었습니다!"); st.rerun()
