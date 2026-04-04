import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- [필수 설정] 구글 드라이브 및 시트 정보 ---
FOLDER_ID = "1RzdmMifRXAJpXQIR5fbipMwFlJEwR7mV"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1h5cEQQGrAIrrpU9qTik8PeUmpRE5zFyW2v1VVNP8e2w/edit?usp=sharing"

# --- 1. 디자인 커스텀 (타이틀 확대 및 폰트) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        
        /* 메인 타이틀 대폭 확대 */
        .main-header { 
            font-size: 48px !important; 
            font-weight: 800; 
            color: #1a1a1a; 
            letter-spacing: -1.5px; 
            margin: 30px 0; 
        }
        
        /* 섹션 타이틀 */
        .s-title { 
            font-size: 22px !important; 
            font-weight: 700; 
            color: #222; 
            border-left: 6px solid #CC0000; 
            padding-left: 12px; 
            margin-bottom: 20px; 
        }
        
        /* 버튼 스타일 */
        .stButton button { border-radius: 6px; font-weight: 600; transition: all 0.2s; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 구글 서비스 연결 함수 (보정 로직 포함) ---
@st.cache_resource
def get_connection():
    try:
        conf = st.secrets.connections.gsheets.to_dict()
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n").replace("\n", "\\n")
        return st.connection("gsheets", type=GSheetsConnection, **conf)
    except: return None

try:
    conn = get_connection()
    def load_crm_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl="0s")
    def load_user_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Users", ttl="0s")
    def save_crm_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
    def save_user_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=df)

    def get_drive_service():
        conf = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n").replace("\n", "\\n")
        creds = service_account.Credentials.from_service_account_info(conf)
        return build('drive', 'v3', credentials=creds)

    def upload_to_drive(file, filename):
        service = get_drive_service()
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype='application/octet-stream', resumable=True)
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        service.permissions().create(fileId=uploaded_file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
        return uploaded_file.get('webViewLink')

    # 데이터 로드
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
    curator_list = list(user_db.keys())

except Exception as e:
    st.error(f"🚨 연결 실패: {e}")
    st.stop()

# --- 3. 로그인 시스템 ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center;">🔐 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("USER ID", curator_list)
    p = st.text_input("PASSWORD", type="password")
    if st.button("SIGN IN"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 4. 메인 화면 ---
df = load_crm_data()
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_name}")
    if st.button("🚪 LOGOUT"): st.session_state.logged_in = False; st.rerun()

# --- 5. 고객 등록 및 리스트 (v7.6 방식 완벽 복구) ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        date = st.date_input("기준일", datetime.now())
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("시스템 저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(date), "모델": mdl, "단계": step, "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "", "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_crm_data(df); st.rerun()

with col_view:
    # 팀장님이 찾으시던 4개 탭 복구!
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체 현황", "📝 계약 현황", "🚚 인도 및 사후관리", "🚫 취소"])
    
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": view_df = view_df[view_df['담당자'] == st.session_state.user_name]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 담당: {row['담당자']} | {row['단계']}"):
                if row['단계'] == "인도완료":
                    st.markdown("**📄 서류 및 1, 3, 6, 12개월 관리**")
                    up_file = st.file_uploader(f"서류 업로드", type=['jpg', 'pdf'], key=f"f_{prefix}_{cid}")
                    if st.button("🚀 드라이브 저장", key=f"u_{prefix}_{cid}"):
                        if up_file:
                            link = upload_to_drive(up_file, f"{row['고객명']}_서류")
                            df.at[idx, '비고'] = link
                            save_crm_data(df); st.rerun()
                    
                    # 사후관리 스케줄러 복구
                    base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                    cols = st.columns(4)
                    for i, p in enumerate([1, 3, 6, 12]):
                        with cols[i]:
                            st.write(f"**{p}개월**"); st.caption(f"📅 {(base_d + relativedelta(months=p)).strftime('%m/%d')}")
                            s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                            is_s = st.checkbox("완료", value=bool(row[s_col]), key=f"s_{prefix}_{idx}_{p}")
                            m_txt = st.text_area("내용", value=row[m_col], key=f"m_{prefix}_{idx}_{p}", height=80)
                            if st.button("저장", key=f"b_{prefix}_{idx}_{p}"):
                                df.at[idx, s_col] = 1 if is_s else 0
                                df.at[idx, m_col] = m_txt
                                save_crm_data(df); st.rerun()
                
                st.divider()
                note = st.text_area("🗒️ 비고", value=row['비고'] if pd.notna(row['비고']) and "http" not in str(row['비고']) else "", key=f"n_{prefix}_{cid}")
                if st.button("비고 저장", key=f"nb_{prefix}_{cid}"):
                    df.at[idx, '비고'] = note
                    save_crm_data(df); st.rerun()

                c1, c2 = st.columns(2)
                if row['단계'] == "계약완료":
                    if c1.button("🚚 인도 완료", key=f"ok_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = str(datetime.now().date())
                        save_crm_data(df); st.rerun()
                    if c2.button("🚫 취소", key=f"can_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약취소"; save_crm_data(df); st.rerun()
                elif row['단계'] == "계약취소":
                    if st.button("계약 복구", key=f"res_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약완료"; save_crm_data(df); st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == "계약완료"], "con")
    with t_del: display_list(view_df[view_df['단계'] == "인도완료"], "del")
    with t_can: display_list(view_df[view_df['단계'] == "계약취소"], "can")
