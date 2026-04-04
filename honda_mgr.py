import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v15.0 Final", layout="wide")

# --- 2. 데이터 연결 및 로드 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)
    def save_user_data(df): conn.update(worksheet="Users", data=df)

    user_df = load_user_data()
    # 데이터 타입을 문자열로 강제 변환하여 매칭 오류 방지
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error("🚨 구글 시트 연결 실패! Secrets 설정을 다시 확인해주세요.")
    st.code(str(e))
    st.stop()

# --- 3. 로그인 시스템 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    with st.container():
        input_user = st.selectbox("사용자 선택", curator_list)
        input_pw = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if user_db.get(input_user) == input_pw:
                st.session_state.logged_in = True
                st.session_state.user_name = input_user
                st.rerun()
            else: st.error("비밀번호가 일치하지 않습니다.")
    st.stop()

# --- 4. 메인 대시보드 ---
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

# 사이드바 로그아웃
if st.sidebar.button("🚪 로그아웃"):
    st.session_state.logged_in = False; st.rerun()

# --- 5. 레이아웃: 등록 및 관리 ---
col_reg, col_view = st.columns([1, 2.5])

with col_reg:
    st.subheader("📍 신규 고객 등록")
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시트에 저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {
                    "ID": new_id, "고객명": name, "담당자": st.session_state.user_name,
                    "기준일": str(datetime.now().date()), "모델": mdl, "단계": step,
                    "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                    "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_crm_data(df); st.success(f"{name}님 등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del = st.tabs(["📊 전체 현황", "📝 계약 관리", "🚚 인도/사후관리"])
    
    # 담당자 필터링 (팀장님은 전체, 나머지는 본인 것만)
    view_df = df.copy()
    if st.session_state.user_name != "박스테반":
        view_df = view_df[view_df['담당자'] == st.session_state.user_name]

    with t_all:
        st.dataframe(view_df, use_container_width=True)

    with t_con:
        con_df = view_df[view_df['단계'] == '계약완료']
        for idx, row in con_df.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']})"):
                if st.button("🚚 인도 완료로 변경", key=f"del_{row['ID']}"):
                    df.loc[df['ID'] == row['ID'], '단계'] = "인도완료"
                    df.loc[df['ID'] == row['ID'], '기준일'] = str(datetime.now().date())
                    save_crm_data(df); st.rerun()

    with t_del:
        del_df = view_df[view_df['단계'] == '인도완료']
        for idx, row in del_df.iterrows():
            with st.expander(f"✅ {row['고객명']} (사후 관리)"):
                st.write(f"인도일: {row['기준일']}")
                note = st.text_area("메모/비고", value=row['비고'] if pd.notna(row['비고']) else "", key=f"n_{row['ID']}")
                if st.button("저장", key=f"s_{row['ID']}"):
                    df.loc[df['ID'] == row['ID'], '비고'] = note
                    save_crm_data(df); st.success("저장되었습니다."); st.rerun()
