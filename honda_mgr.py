import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- [설정] 파일 경로 및 드라이브 폴더 ---
CRM_FILE = "crm_data.csv"
USER_FILE = "users.csv"
FOLDER_ID = "1RzdmMifRXAJpXQIR5fbipMwFlJEwR7mV"

# --- 1. 디자인 커스텀 (타이틀 확대 및 전문가용 서체) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        
        /* 메인 타이틀 강조 */
        .main-header { 
            font-size: 40px !important; 
            font-weight: 800; 
            color: #1a1a1a; 
            letter-spacing: -1.5px; 
            margin-bottom: 10px;
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
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 (GitHub 파일 기반) ---
def load_data(file_path, columns):
    if os.path.exists(file_path):
        return pd.read_csv(file_path).fillna("")
    return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

# 구글 드라이브 서비스 (파일 업로드 기능만 유지)
def get_drive_service():
    try:
        conf = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n")
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

# --- 3. 로그인 및 사용자 데이터 ---
user_df = load_data(USER_FILE, ["ID", "Password"])
user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
curator_list = list(user_db.keys())

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">🔐 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER ID", curator_list if curator_list else ["박스테반"])
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_data(CRM_FILE, ["ID", "고객명", "담당자", "기준일", "모델", "단계", "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"])

# --- 5. 타이틀 및 사이드바 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">Current User: {st.session_state.user_name}</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"**{st.session_state.user_name}**")
    if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    with st.expander("비밀번호 변경"):
        new_pw = st.text_input("새 비밀번호", type="password")
        if st.button("Update"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = new_pw
            save_data(user_df, USER_FILE); st.success("변경 완료"); st.rerun()

# 팀장 전용 인수인계 (박스테반 전용)
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구"):
        m_tab1, m_tab2 = st.tabs(["🔍 필터", "🔄 인수인계"])
        with m_tab1: selected_curator = st.selectbox("조회 담당자 선택", ["전체 보기"] + curator_list)
        with m_tab2:
            src = st.selectbox("기존 담당자", curator_list)
            tgt = st.selectbox("인수자", [c for c in curator_list if c != src])
            target_ids = st.multiselect("대상 고객", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인수인계 실행") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_data(df, CRM_FILE); st.success("완료"); st.rerun()

st.divider()

# --- 6. 고객 등록 및 리스트 (v7.6 레이아웃 완벽 복구) ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("시스템 저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_data(df, CRM_FILE); st.success("등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도 및 사후관리", "🚫 취소"])
    
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": 
        view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기": 
        view_df = view_df[view_df['담당자'] == selected_curator]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | {row['단계']}"):
                # 인도 완료 고객 전용
                if row['단계'] == "인도완료":
                    st.markdown("**📄 서류 및 사후관리**")
                    up_file = st.file_uploader(f"서류 업로드", type=['jpg', 'pdf'], key=f"f_{prefix}_{cid}")
                    if st.button("🚀 드라이브 저장", key=f"u_{prefix}_{cid}"):
                        if up_file:
                            link = upload_to_drive(up_file, f"{row['고객명']}_서류")
                            df.at[idx, '비고'] = link
                            save_data(df, CRM_FILE); st.success("저장 성공!"); st.rerun()
                    if "http" in str(row['비고']): st.link_button("📂 서류 보기", row['비고'])

                st.divider()
                # 비고 및 버튼
                note = st.text_area("🗒️ 비고 및 특이사항", value=row['비고'] if pd.notna(row['비고']) and "http" not in str(row['비고']) else "", key=f"n_{prefix}_{cid}")
                if st.button("저장", key=f"nb_{prefix}_{cid}"):
                    df.at[idx, '비고'] = note
                    save_data(df, CRM_FILE); st.success("저장됨"); st.rerun()

                c1, c2 = st.columns(2)
                if row['단계'] == "계약완료":
                    if c1.button("🚚 인도 완료 처리", key=f"ok_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = str(datetime.now().date())
                        save_data(df, CRM_FILE); st.rerun()
                    if c2.button("🚫 취소 처리", key=f"no_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약취소"; save_data(df, CRM_FILE); st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
    with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
    with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
