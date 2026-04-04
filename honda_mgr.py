import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v19.0 Final", layout="wide")

# --- 2. 데이터 연결 및 로드 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    def load_crm_data(): return conn.read(worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(worksheet="Sheet1", data=df)
    def save_user_data(df): conn.update(worksheet="Users", data=df)

    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())
except Exception as e:
    st.error("🚨 데이터 연결 실패! Secrets 설정과 구글 시트 공유 권한을 확인하세요.")
    st.warning(f"🔍 진짜 에러 이유: {e}") # 이 줄을 추가하면 이유가 화면에 뜹니다!
    st.info(f"💡 팁: 서비스 계정 이메일을 새 시트에 '편집자'로 추가하셨나요?")
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
            else: st.error("정보가 일치하지 않습니다.")
    st.stop()

# --- 4. 메인 화면 ---
df = load_crm_data()
st.title(f"🚗 {st.session_state.user_name} 팀장님 관리 보드")

# 사이드바 (로그아웃 및 관리자 도구)
with st.sidebar:
    st.subheader(f"사용자: {st.session_state.user_name}")
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False; st.rerun()
    st.divider()
    
    sel_cur = "전체 보기"
    if st.session_state.user_name == "박스테반":
        st.write("🛠️ 관리자 필터")
        sel_cur = st.selectbox("큐레이터 선택", ["전체 보기"] + curator_list)

# --- 5. 신규 고객 등록 ---
with st.expander("➕ 신규 고객 등록", expanded=False):
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시트에 저장"):
            if name:
                new_id = 1 if df.empty or 'ID' not in df.columns else int(df['ID'].max()) + 1
                new_row = {
                    "ID": new_id, "고객명": name, "담당자": st.session_state.user_name,
                    "기준일": str(datetime.now().date()), "모델": mdl, "단계": step,
                    "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                    "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_crm_data(df); st.success(f"✅ {name}님 등록 완료!"); st.rerun()

# --- 6. 고객 관리 탭 ---
t_all, t_con, t_del = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도/사후관리"])

# 필터링 적용
view_df = df.copy()
if st.session_state.user_name != "박스테반":
    view_df = view_df[view_df['담당자'] == st.session_state.user_name]
elif sel_cur != "전체 보기":
    view_df = view_df[view_df['담당자'] == sel_cur]

with t_all:
    st.dataframe(view_df, use_container_width=True)

with t_con:
    con_df = view_df[view_df['단계'] == '계약완료']
    for idx, row in con_df.iterrows():
        with st.expander(f"📌 {row['고객명']} ({row['모델']})"):
            if st.button("🚚 인도 완료 처리", key=f"del_{row['ID']}"):
                df.loc[df['ID'] == row['ID'], '단계'] = "인도완료"
                df.loc[df['ID'] == row['ID'], '기준일'] = str(datetime.now().date())
                save_crm_data(df); st.rerun()

with t_del:
    del_df = view_df[view_df['단계'] == '인도완료']
    for idx, row in del_df.iterrows():
        with st.expander(f"✅ {row['고객명']} 사후 관리"):
            st.write(f"인도일: {row['기준일']}")
            # 비고/서류링크 관리
            note = st.text_area("비고 (서류링크 등)", value=row['비고'] if '비고' in df.columns and pd.notna(row['비고']) else "", key=f"n_{row['ID']}")
            if st.button("내용 저장", key=f"s_{row['ID']}"):
                df.loc[df['ID'] == row['ID'], '비고'] = note
                save_crm_data(df); st.success("시트 업데이트 완료!"); st.rerun()
