import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 및 디자인 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 40px; font-weight: 800; color: #1a1a1a; margin-bottom: 30px; }
        .s-title { font-size: 22px; font-weight: 700; color: #222; border-left: 6px solid #CC0000; padding-left: 12px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 초기화 (앱 실행 동안 유지) ---
if 'crm_db' not in st.session_state:
    st.session_state.crm_db = pd.DataFrame(columns=[
        "ID", "고객명", "담당자", "기준일", "모델", "단계", 
        "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", 
        "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"
    ])

# --- 3. 로그인 시스템 ---
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

# --- 4. 상단 타이틀 및 백업 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

with st.sidebar:
    st.write(f"**접속자: {st.session_state.user_name}**")
    # [백업 기능] 저장이 불안할 때 언제든 내 컴퓨터로 엑셀 저장
    csv = st.session_state.crm_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 데이터 백업(CSV)", data=csv, file_name=f"honda_crm_{datetime.now().strftime('%m%d')}.csv")
    if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()

# --- 5. 고객 등록 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_id = len(st.session_state.crm_db) + 1
                new_row = {
                    "ID": new_id, "고객명": name, "담당자": st.session_state.user_name, 
                    "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": "",
                    "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                    "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": ""
                }
                st.session_state.crm_db = pd.concat([st.session_state.crm_db, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                st.success(f"{name}님 등록 완료!"); st.rerun()

# --- 6. 현황 관리 (사후관리 완벽 복구) ---
with col_view:
    t_all, t_del = st.tabs(["📊 전체 현황", "🚚 인도 및 사후관리"])
    
    # 내 데이터만 보기 필터
    df = st.session_state.crm_db
    view_df = df[df['담당자'] == st.session_state.user_name] if st.session_state.user_name != "박스테반" else df

    with t_all:
        st.dataframe(view_df, use_container_width=True)

    with t_del:
        target_df = view_df[view_df['단계'] == "인도완료"]
        if target_df.empty: st.info("인도 완료된 고객이 없습니다.")
        for idx, row in target_df.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 인도일: {row['기준일']}"):
                # [여기가 핵심!] 1, 3, 6, 12개월 관리 칸 복구
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.markdown(f"**{p}개월 차**")
                        st.caption(f"📅 {(base_d + relativedelta(months=p)).strftime('%m/%d')}")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        
                        # 값 업데이트 로직
                        checked = st.checkbox("발송", value=bool(row[s_col]), key=f"s_{idx}_{p}")
                        msg = st.text_area("메시지 내용", value=row[m_col], key=f"m_{idx}_{p}", height=80)
                        if st.button("저장", key=f"b_{idx}_{p}"):
                            st.session_state.crm_db.at[idx, s_col] = 1 if checked else 0
                            st.session_state.crm_db.at[idx, m_col] = msg
                            st.success("기록 완료"); st.rerun()
                
                st.divider()
                note = st.text_area("🗒️ 특이사항/비고", value=row['비고'], key=f"n_{idx}")
                if st.button("비고 저장", key=f"nb_{idx}"):
                    st.session_state.crm_db.at[idx, '비고'] = note
                    st.rerun()
