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

# --- 1. 세련된 UI를 위한 CSS 적용 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Noto+Sans+KR', sans-serif; }
        .main-title { font-size: 32px; font-weight: 700; color: #1E1E1E; margin-bottom: 20px; letter-spacing: -1px; }
        .sub-title { font-size: 18px; font-weight: 700; color: #444; margin-bottom: 10px; border-left: 4px solid #CC0000; padding-left: 10px; }
        .stButton button { width: 100%; border-radius: 5px; background-color: #f8f9fa; color: #333; border: 1px solid #ddd; }
        .stButton button:hover { background-color: #CC0000; color: white; border: 1px solid #CC0000; }
        .stExpander { border-radius: 10px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 ---
def load_data(file_path, columns):
    if os.path.exists(file_path):
        return pd.read_csv(file_path).fillna("")
    return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    # 이 함수가 실행될 때 깃허브의 파일이 실제로 업데이트됩니다.
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
    st.markdown('<p class="main-title">🔐 CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER", curator_list if curator_list else ["박스테반"])
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
        else: st.error("Access Denied.")
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_data(CRM_FILE, ["ID", "고객명", "담당자", "기준일", "모델", "단계", "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"])

# --- 5. 레이아웃 ---
st.markdown('<p class="main-title">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"**Current User:** {st.session_state.user_name}")
    if st.button("LOGOUT"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    with st.expander("비밀번호 변경"):
        pw = st.text_input("New Password", type="password")
        if st.button("Update"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = pw
            save_data(user_df, USER_FILE); st.success("Updated Successfully"); st.rerun()

selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    selected_curator = st.selectbox("조회 담당자 필터", ["전체 보기"] + curator_list)

st.divider()

# --- 6. 기능부 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<p class="sub-title">고객 신규 등록</p>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        n = st.text_input("고객명")
        m = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        s = st.radio("현 단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if n:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": n, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": m, "단계": s, "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_data(df, CRM_FILE); st.rerun()

with col_view:
    t1, t2, t3 = st.tabs(["📊 전체 현황", "🚚 인도 및 사후관리", "🔄 인수인계"])
    
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기": view_df = view_df[view_df['담당자'] == selected_curator]

    with t1: st.dataframe(view_df, use_container_width=True)

    with t2:
        del_df = view_df[view_df['단계'] == "인도완료"]
        for idx, row in del_df.iterrows():
            with st.expander(f"📍 {row['고객명']} ({row['모델']}) | 인도일: {row['기준일']}"):
                # 사후관리 메시지 기록
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.markdown(f"**{p}개월 차**")
                        st.caption(f"{(base_d + relativedelta(months=p)).strftime('%Y-%m-%d')}")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("발송완료", value=bool(row[s_col]), key=f"s_{idx}_{p}")
                        m_txt = st.text_area("메시지 내용", value=row[m_col], key=f"m_{idx}_{p}", height=120)
                        if st.button("저장", key=f"b_{idx}_{p}"):
                            df.at[idx, s_col] = 1 if is_s else 0
                            df.at[idx, m_col] = m_txt
                            save_data(df, CRM_FILE); st.rerun()
                
                st.divider()
                # 하단 통합 비고란
                note = st.text_area("🗒️ 전체 비고 및 특이사항", value=row['비고'], key=f"note_{idx}")
                if st.button("비고 내용 저장", key=f"nb_{idx}"):
                    df.at[idx, '비고'] = note
                    save_data(df, CRM_FILE); st.success("비고 저장됨"); st.rerun()

    with t3:
        if st.session_state.user_name == "박스테반":
            st.markdown('<p class="sub-title">업무 인수인계</p>', unsafe_allow_html=True)
            src = st.selectbox("기존 담당자", curator_list)
            tgt = st.selectbox("신규 담당자", [c for c in curator_list if c != src])
            target_ids = st.multiselect("대상 고객 선택", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인수인계 실행") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_data(df, CRM_FILE); st.success("업무 이관 완료"); st.rerun()
