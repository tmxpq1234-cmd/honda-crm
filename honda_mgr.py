import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- [필수 설정] 구글 드라이브 폴더 ID ---
FOLDER_ID = "1RzdmMifRXAJpXQIR5fbipMwFlJEwR7mV"

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v7.7 Final", layout="wide")

st.markdown("""
    <style>
        .s-title { white-space: nowrap; font-size: 21px !important; font-weight: bold; margin-bottom: 15px; }
        .stButton button { width: 100%; }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 18px; font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 구글 서비스 연결 설정 (PEM 파일 규칙 자동 해결 로직) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1h5cEQQGrAIrrpU9qTik8PeUmpRE5zFyW2v1VVNP8e2w/edit?usp=sharing"

@st.cache_resource
def get_connection():
    try:
        # Secrets 데이터를 딕셔너리로 가져옵니다.
        raw_conf = st.secrets["connections"]["gsheets"].to_dict()
        
        # [핵심 수정] PEM 파일의 줄바꿈(\n) 문제를 기계가 자동으로 해결하도록 합니다.
        if "private_key" in raw_conf:
            # 역슬래시 n을 진짜 엔터로 바꾸고 앞뒤 공백을 제거하여 64자 규칙 에러를 방지합니다.
            raw_conf["private_key"] = raw_conf["private_key"].replace("\\n", "\n").strip()
        
        # GSheetsConnection을 직접 명시하여 'service_account' 인식 오류를 방지합니다.
        return st.connection("gsheets", type=GSheetsConnection, **raw_conf)
    except Exception as e:
        st.error(f"❌ 연결 초기화 오류: {e}")
        st.stop()

conn = get_connection()

# 데이터 로드/저장 함수
def load_crm_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl="0s")
def load_user_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Users", ttl="0s")
def save_crm_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
def save_user_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=df)

# 구글 드라이브 서비스 인증 (세척된 키 사용)
def get_drive_service():
    conf = st.secrets["connections"]["gsheets"].to_dict()
    conf["private_key"] = conf["private_key"].replace("\\n", "\n").strip()
    creds = service_account.Credentials.from_service_account_info(conf)
    return build('drive', 'v3', credentials=creds)

# 파일 업로드 함수
def upload_to_drive(file, filename):
    service = get_drive_service()
    file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype='application/octet-stream', resumable=True)
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    service.permissions().create(fileId=uploaded_file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
    return uploaded_file.get('webViewLink')

# --- 3. 로그인 시스템 ---
try:
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'], user_df['Password']))
    curator_list = list(user_db.keys())
except Exception as e:
    st.error(f"⚠️ 'Users' 탭 로드 실패: {e}")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    input_user = st.selectbox("사용자 선택", curator_list)
    input_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(input_user) == input_pw:
            st.session_state.logged_in = True
            st.session_state.user_name = input_user
            st.rerun()
        else: st.error("비밀번호 불일치")
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_crm_data()

# --- 5. 사이드바 ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user_name} 팀장님")
    with st.expander("🔐 비밀번호 변경"):
        new_pw = st.text_input("새 비밀번호", type="password", key="sidebar_new_pw")
        if st.button("변경 저장"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = new_pw
            save_user_data(user_df)
            st.success("✅ 변경 완료!")
            st.rerun()
    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

st.title("🚗 Honda 통합 고객 관리 시스템")

# --- 6. 팀장 관리 도구 ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구"):
        m_tab1, m_tab2, m_tab3 = st.tabs(["🔍 필터", "👥 인사", "🔄 인계"])
        with m_tab1: selected_curator = st.selectbox("담당자 선택", ["전체 보기"] + curator_list)
        with m_tab2:
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                new_n = st.text_input("신입 이름")
                if st.button("✨ 등록"):
                    user_df = pd.concat([user_df, pd.DataFrame([{"ID": new_n, "Password": "honda2024"}])], ignore_index=True)
                    save_user_data(user_df); st.rerun()
            with u_col2:
                del_n = st.selectbox("퇴사자", [c for c in curator_list if c != "박스테반"])
                if st.button("🗑️ 삭제"):
                    user_df = user_df[user_df['ID'] != del_n]
                    save_user_data(user_df); st.rerun()
        with m_tab3:
            src = st.selectbox("기존 담당자", curator_list)
            tgt = st.selectbox("인수자", [c for c in curator_list if c != src])
            target_ids = st.multiselect("고객 선택", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인계 실행") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_crm_data(df); st.success("인계 완료!"); st.rerun()

st.divider()

# --- 7. 메인 화면 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        date = st.date_input("기준일", datetime.now())
        cur = st.selectbox("담당자", curator_list, index=curator_list.index(st.session_state.user_name))
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": name, "담당자": cur, "기준일": str(date), "모델": mdl, "단계": step,
                           "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                           "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_crm_data(df); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체", "📝 계약", "🚚 인도", "🚫 취소"])
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기": view_df = view_df[view_df['담당자'] == selected_curator]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 [{row['단계']}] {row['고객명']} ({row['모델']}) - {row['담당자']}"):
                if row['단계'] == "인도완료":
                    st.markdown("### 📄 서류 관리")
                    up_file = st.file_uploader("파일 선택", type=['jpg', 'png', 'pdf'], key=f"f_{prefix}_{cid}")
                    if st.button("🚀 업로드", key=f"ub_{prefix}_{cid}"):
                        if up_file:
                            link = upload_to_drive(up_file, f"{row['고객명']}_서류")
                            df.at[idx, '비고'] = link
                            save_crm_data(df); st.success("완료!"); st.rerun()
                    if pd.notna(row['비고']) and "http" in str(row['비고']):
                        st.link_button("📂 파일 열기", row['비고'], key=f"vd_{prefix}_{cid}")
                    
                    st.divider()
                    try:
                        base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                        cols = st.columns(4)
                        for i, p in enumerate([1, 3, 6, 12]):
                            t_date = (base_d + relativedelta(months=p)).strftime('%Y-%m-%d')
                            with cols[i]:
                                st.write(f"**{p}개월**"); st.caption(t_date)
                                s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                                is_s = st.checkbox("완료", value=bool(row[s_col]), key=f"s_{prefix}_{p}_{cid}")
                                m_txt = st.text_area("메모", value=row[m_col] if pd.notna(row[m_col]) else "", key=f"m_{prefix}_{p}_{cid}", height=70)
                                if st.button("저장", key=f"b_{prefix}_{p}_{cid}"):
                                    df.at[idx, s_col] = 1 if is_s else 0
                                    df.at[idx, m_col] = m_txt
                                    save_crm_data(df); st.rerun()
                    except: pass

                if row['단계'] == "계약완료":
                    c1, c2 = st.columns(2)
                    if c1.button("🚚 인도 완료 처리", key=f"d_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = datetime.now().strftime('%Y-%m-%d')
                        save_crm_data(df); st.rerun()
                    if c2.button("🚫 계약 취소", key=f"c_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약취소"; save_crm_data(df); st.rerun()
                elif row['단계'] == "계약취소":
                    if st.button("🔄 계약 복구", key=f"res_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약완료"; save_crm_data(df); st.rerun()
                
                st.divider()
                note_val = row['비고'] if pd.notna(row['비고']) and "http" not in str(row['비고']) else ""
                note = st.text_area("특이사항", value=note_val, key=f"n_{prefix}_{cid}")
                if st.button("비고 저장", key=f"nb_{prefix}_{cid}"):
                    df.at[idx, '비고'] = note
                    save_crm_data(df); st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == '계약완료'], "con")
    with t_del: display_list(view_df[view_df['단계'] == '인도완료'], "del")
    with t_can: display_list(view_df[view_df['단계'] == '계약취소'], "can")
