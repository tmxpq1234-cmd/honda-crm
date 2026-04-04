import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- 설정 및 파일 경로 ---
FOLDER_ID = "1RzdmMifRXAJpXQIR5fbipMwFlJEwR7mV"
CRM_FILE = "crm_data.csv"
USER_FILE = "users.csv"

# --- 1. 세련된 전문가용 디자인 설정 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        
        /* 전체 폰트 및 배경 */
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
        .main { background-color: #fcfcfc; }
        
        /* 타이틀 디자인 */
        .main-header { font-size: 28px; font-weight: 800; color: #1a1a1a; margin-bottom: 5px; letter-spacing: -1px; }
        .sub-header { font-size: 14px; color: #666; margin-bottom: 30px; }
        
        /* 섹션 타이틀 */
        .section-title { font-size: 19px; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin: 25px 0 15px 0; }
        
        /* 버튼 디자인 */
        .stButton button { border-radius: 6px; font-weight: 600; transition: all 0.2s; border: 1px solid #ddd; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; border: 1px solid #CC0000 !important; }
        
        /* 데이터프레임 및 카드 */
        .stDataFrame { border-radius: 10px; overflow: hidden; }
        .stExpander { border: 1px solid #eee !important; border-radius: 8px !important; background-color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 ---
def load_data(file_path, columns):
    if os.path.exists(file_path):
        return pd.read_csv(file_path).fillna("")
    return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def get_drive_service():
    try:
        conf = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n").replace("\n", "\\n")
        creds = service_account.Credentials.from_service_account_info(conf)
        return build('drive', 'v3', credentials=creds)
    except: return None

def upload_to_drive(file, filename):
    service = get_drive_service()
    if not service: return None
    file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype='application/octet-stream', resumable=True)
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    service.permissions().create(fileId=uploaded_file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
    return uploaded_file.get('webViewLink')

# --- 3. 로그인 시스템 ---
user_df = load_data(USER_FILE, ["ID", "Password"])
user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
curator_list = list(user_db.keys())

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<div style="text-align:center; padding: 50px 0;">', unsafe_allow_html=True)
    st.markdown('<p class="main-header">HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER ID", curator_list if curator_list else ["박스테반"])
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
        else: st.error("Access Denied.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_data(CRM_FILE, ["ID", "고객명", "담당자", "기준일", "모델", "단계", "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"])

# --- 5. 상단 헤더 및 사이드바 ---
st.markdown('<p class="main-header">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">접속자: {st.session_state.user_name}</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"**{st.session_state.user_name}**")
    if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    with st.expander("비밀번호 변경"):
        pw = st.text_input("New Password", type="password")
        if st.button("Update"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = pw
            save_data(user_df, USER_FILE); st.success("Updated"); st.rerun()

# --- 6. 팀장 전용 기능 (박스테반 전용) ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구 (인수인계 및 필터)"):
        m_tab1, m_tab2 = st.tabs(["🔍 데이터 필터", "🔄 업무 인수인계"])
        with m_tab1: 
            selected_curator = st.selectbox("조회 담당자 선택", ["전체 보기"] + curator_list)
        with m_tab2:
            st.markdown("**고객DB 담당자 변경**")
            src = st.selectbox("기존 담당자", curator_list, key="src_insu")
            tgt = st.selectbox("인수자", [c for c in curator_list if c != src], key="tgt_insu")
            target_ids = st.multiselect("대상 고객", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인수인계 확정") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_data(df, CRM_FILE); st.success("인수인계 완료"); st.rerun()

st.divider()

# --- 7. 메인 업무 로직 (v7.6 세로 틀 복구) ---

# [1] 신규 등록 섹션
st.markdown('<p class="section-title">📍 고객 신규 등록</p>', unsafe_allow_html=True)
with st.form("reg_form", clear_on_submit=True):
    r_col1, r_col2, r_col3 = st.columns(3)
    with r_col1: n = st.text_input("고객명")
    with r_col2: m = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
    with r_col3: s = st.selectbox("현 단계", ["계약완료", "인도완료"])
    if st.form_submit_button("시스템 저장"):
        if n:
            new_id = int(df['ID'].max()) + 1 if not df.empty else 1
            new_row = {"ID": new_id, "고객명": n, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": m, "단계": s, "비고": ""}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
            save_data(df, CRM_FILE); st.rerun()

# [2] 고객 리스트 및 사후관리
st.markdown('<p class="section-title">📊 현황 관리 및 사후 스케줄</p>', unsafe_allow_html=True)
t_all, t_con, t_del, t_can = st.tabs(["전체", "계약", "인도/사후관리", "취소"])

# 데이터 필터링
view_df = df.copy()
if st.session_state.user_name != "박스테반": 
    view_df = view_df[view_df['담당자'] == st.session_state.user_name]
elif selected_curator != "전체 보기": 
    view_df = view_df[view_df['담당자'] == selected_curator]

def display_list(target_df, prefix):
    if target_df.empty: st.caption("해당하는 데이터가 없습니다.")
    for idx, row in target_df.iterrows():
        cid = row['ID']
        with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 담당: {row['담당자']} | {row['단계']}"):
            # 사후관리 (인도완료 고객만)
            if row['단계'] == "인도완료":
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                st.markdown("**📅 정기 사후관리 메시지 기록**")
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.caption(f"{p}개월 ({(base_d + relativedelta(months=p)).strftime('%m/%d')})")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("완료", value=bool(row[s_col]), key=f"s_{prefix}_{idx}_{p}")
                        m_txt = st.text_area("메시지 내용", value=row[m_col], key=f"m_{prefix}_{idx}_{p}", height=80)
                        if st.button("저장", key=f"b_{prefix}_{idx}_{p}"):
                            df.at[idx, s_col] = 1 if is_s else 0
                            df.at[idx, m_col] = m_txt
                            save_data(df, CRM_FILE); st.rerun()
                st.divider()

            # 공통 비고란
            note = st.text_area("🗒️ 전체 비고 및 서류링크", value=row['비고'], key=f"note_{prefix}_{idx}")
            if st.button("비고 저장", key=f"nb_{prefix}_{idx}"):
                df.at[idx, '비고'] = note
                save_data(df, CRM_FILE); st.rerun()
            
            # 상태 변경 버튼
            c1, c2 = st.columns(2)
            if row['단계'] == "계약완료":
                if c1.button("🚚 인도 완료 처리", key=f"ok_{prefix}_{idx}"):
                    df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = str(datetime.now().date())
                    save_data(df, CRM_FILE); st.rerun()
                if c2.button("🚫 계약 취소", key=f"no_{prefix}_{idx}"):
                    df.at[idx, '단계'] = "계약취소"; save_data(df, CRM_FILE); st.rerun()

with t_all: st.dataframe(view_df[view_df['단계'] != '계약취소'], use_container_width=True)
with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
