import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 및 전문가용 디자인 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        
        /* 메인 타이틀 크게 확대 */
        .main-header { 
            font-size: 45px !important; 
            font-weight: 800; 
            color: #1a1a1a; 
            margin-bottom: 5px;
            letter-spacing: -1.5px;
        }
        .sub-header { font-size: 16px; color: #666; margin-bottom: 30px; }
        
        /* 섹션 타이틀 */
        .s-title { 
            font-size: 22px !important; 
            font-weight: 700; 
            color: #222; 
            border-left: 6px solid #CC0000; 
            padding-left: 12px; 
            margin-bottom: 20px; 
        }

        /* 버튼 디자인 */
        .stButton button { border-radius: 6px; font-weight: 600; transition: all 0.2s; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; border-color: #CC0000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 (GitHub 파일 직접 읽기/쓰기 아님 - 휘발 방지용 세션 사용) ---
# ※ 주의: Streamlit Cloud 특성상 깃허브 파일에 직접 '쓰기'는 권한 문제로 매우 까다롭습니다.
# 일단 '세션 저장' 방식을 쓰고, 하단에 [백업] 버튼을 통해 데이터를 지킬 수 있게 했습니다.

if 'crm_db' not in st.session_state:
    # 최초 실행 시 비어있는 데이터프레임 생성
    st.session_state.crm_db = pd.DataFrame(columns=[
        "ID", "고객명", "담당자", "기준일", "모델", "단계", 
        "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", 
        "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"
    ])

# --- 3. 로그인 시스템 (고정 명단) ---
USER_DB = {
    "박스테반": "1234", 
    "김태형": "2290", 
    "전유인": "2290", 
    "전명현": "2290", 
    "이준창": "2290"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">🔐 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER ID", list(USER_DB.keys()))
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if USER_DB.get(u) == p:
            st.session_state.logged_in = True
            st.session_state.user_name = u
            st.rerun()
        else: st.error("비밀번호를 확인해주세요.")
    st.stop()

# --- 4. 메인 화면 레이아웃 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Current User: {st.session_state.user_name}</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_name}")
    # [백업 기능] 데이터가 날아가지 않게 수시로 다운로드하세요.
    csv = st.session_state.crm_db.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 데이터 다운로드(백업)", data=csv, file_name=f"honda_crm_data.csv", mime="text/csv")
    if st.button("🚪 LOGOUT"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. 고객 등록 및 리스트 (v7.6 레이아웃 완벽 복구) ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("시스템 저장"):
            if name:
                new_id = len(st.session_state.crm_db) + 1
                new_row = {
                    "ID": new_id, "고객명": name, "담당자": st.session_state.user_name, 
                    "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, 
                    "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                    "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""
                }
                st.session_state.crm_db = pd.concat([st.session_state.crm_db, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                st.success("등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도 및 사후관리", "🚫 취소"])
    
    # 내 데이터 필터링
    df = st.session_state.crm_db
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    def display_list(target_df, prefix):
        if target_df.empty: st.info("표시할 데이터가 없습니다.")
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 담당: {row['담당자']} | {row['단계']}"):
                
                # [인도완료 전용] 사후관리 스케줄러 (1, 3, 6, 12개월)
                if row['단계'] == "인도완료":
                    st.markdown("**📅 정기 사후관리 (1~12개월)**")
                    base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                    cols = st.columns(4)
                    for i, p in enumerate([1, 3, 6, 12]):
                        with cols[i]:
                            st.write(f"**{p}개월**")
                            st.caption(f"📅 {(base_d + relativedelta(months=p)).strftime('%m/%d')}")
                            s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                            is_s = st.checkbox("발송", value=bool(row[s_col]), key=f"s_{prefix}_{idx}_{p}")
                            m_txt = st.text_area("내용", value=row[m_col], key=f"m_{prefix}_{idx}_{p}", height=80)
                            if st.button("저장", key=f"b_{prefix}_{idx}_{p}"):
                                st.session_state.crm_db.at[idx, s_col] = 1 if is_s else 0
                                st.session_state.crm_db.at[idx, m_col] = m_txt
                                st.rerun()
                    st.divider()

                # 비고란
                note = st.text_area("🗒️ 특이사항 및 비고", value=row['비고'], key=f"n_{prefix}_{idx}")
                if st.button("비고 저장", key=f"nb_{prefix}_{idx}"):
                    st.session_state.crm_db.at[idx, '비고'] = note
                    st.rerun()

                # 상태 제어 버튼
                c1, c2 = st.columns(2)
                if row['단계'] == "계약완료":
                    if c1.button("🚚 인도 완료 처리", key=f"ok_{prefix}_{idx}"):
                        st.session_state.crm_db.at[idx, '단계'] = "인도완료"
                        st.session_state.crm_db.at[idx, '기준일'] = str(datetime.now().date())
                        st.rerun()
                    if c2.button("🚫 취소 처리", key=f"can_{prefix}_{idx}"):
                        st.session_state.crm_db.at[idx, '단계'] = "계약취소"; st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
    with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
    with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
