import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- [필수 설정] 구글 드라이브 폴더 ID (서류 업로드용은 유지) ---
FOLDER_ID = "1RzdmMifRXAJpXQIR5fbipMwFlJEwR7mV"
CRM_FILE = "crm_data.csv"
USER_FILE = "users.csv"

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v25.0 GitHub", layout="wide")

st.markdown("""
    <style>
        .s-title { white-space: nowrap; font-size: 21px !important; font-weight: bold; margin-bottom: 15px; }
        .stButton button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 (GitHub 파일 기반) ---
def load_data(file_path, columns):
    if os.path.exists(file_path):
        return pd.read_csv(file_path).fillna("")
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

# 구글 드라이브 서비스 연결 (서류 업로드 기능용)
def get_drive_service():
    try:
        conf = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in conf:
            conf["private_key"] = conf["private_key"].replace("\\n", "\n").replace("\n", "\\n")
        creds = service_account.Credentials.from_service_account_info(conf)
        return build('drive', 'v3', credentials=creds)
    except:
        return None

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
if user_df.empty:
    user_df = pd.DataFrame([{"ID": "박스테반", "Password": "1234"}])
    save_data(user_df, USER_FILE)

user_db = dict(zip(user_df['ID'].astype(str), user_df['Password'].astype(str)))
curator_list = list(user_db.keys())

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Honda CRM 접속")
    input_user = st.selectbox("사용자 선택", curator_list)
    input_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(input_user) == input_pw:
            st.session_state.logged_in = True
            st.session_state.user_name = input_user
            st.rerun()
        else: st.error("비밀번호를 확인해주세요.")
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_data(CRM_FILE, ["ID", "고객명", "담당자", "기준일", "모델", "단계", "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"])

# --- 5. 사이드바 ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user_name}")
    with st.expander("🔐 내 비밀번호 변경"):
        new_pw = st.text_input("새 비밀번호", type="password")
        if st.button("변경 저장"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = new_pw
            save_data(user_df, USER_FILE); st.success("✅ 변경 완료!"); st.rerun()
    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False; st.rerun()

st.title("🚗 Honda 통합 고객 관리 시스템")

# --- 6. 팀장 전용 도구 (박스테반 팀장님 전용) ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구", expanded=False):
        m_tab1, m_tab2, m_tab3 = st.tabs(["🔍 데이터 필터", "👥 큐레이터 인사 관리", "🔄 업무 인수인계"])
        with m_tab1: selected_curator = st.selectbox("조회할 담당자 선택", ["전체 보기"] + curator_list)
        with m_tab2:
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                new_n = st.text_input("신입 이름")
                if st.button("✨ 등록"):
                    user_df = pd.concat([user_df, pd.DataFrame([{"ID": new_n, "Password": "1234"}])], ignore_index=True)
                    save_data(user_df, USER_FILE); st.rerun()
            with u_col2:
                del_n = st.selectbox("퇴사자", [c for c in curator_list if c != "박스테반"])
                if st.button("🗑️ 삭제"):
                    user_df = user_df[user_df['ID'] != del_n]
                    save_data(user_df, USER_FILE); st.rerun()
        with m_tab3:
            src = st.selectbox("기존 담당자", curator_list)
            tgt = st.selectbox("인수자", [c for c in curator_list if c != src])
            target_ids = st.multiselect("고객 선택", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인수인계 실행") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_data(df, CRM_FILE); st.success("완료!"); st.rerun()

st.divider()

# --- 7. 고객 등록 및 리스트 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        date = st.date_input("기준일", datetime.now())
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        if st.form_submit_button("저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(date), "모델": mdl, "단계": step,
                           "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "", "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_data(df, CRM_FILE); st.success(f"{name}님 등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체", "📝 계약", "🚚 인도", "🚫 취소"])
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기": view_df = view_df[view_df['담당자'] == selected_curator]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 [{row['단계']}] {row['고객명']} ({row['모델']}) - 담당: {row['담당자']}"):
                # [서류 관리 기능]
                if row['단계'] == "인도완료":
                    st.markdown("### 📄 인도 서류 관리")
                    up_file = st.file_uploader(f"서류 업로드", type=['jpg', 'pdf'], key=f"f_{prefix}_{cid}")
                    if st.button("🚀 드라이브에 저장", key=f"u_{prefix}_{cid}"):
                        if up_file:
                            link = upload_to_drive(up_file, f"{row['고객명']}_서류")
                            df.at[idx, '비고'] = link
                            save_data(df, CRM_FILE); st.success("저장 완료!"); st.rerun()
                    if "http" in str(row['비고']): st.link_button("📂 서류 보기", row['비고'])

                    # [사후관리 스케줄러]
                    st.divider()
                    base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                    cols = st.columns(4)
                    for i, p in enumerate([1, 3, 6, 12]):
                        t_date = (base_d + relativedelta(months=p)).strftime('%Y-%m-%d')
                        with cols[i]:
                            st.write(f"**{p}개월**"); st.caption(f"📅 {t_date}")
                            s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                            is_s = st.checkbox("완료", value=bool(row[s_col]), key=f"s_{prefix}_{p}_{cid}")
                            m_txt = st.text_area("메모", value=row[m_col], key=f"m_{prefix}_{p}_{cid}", height=70)
                            if st.button("저장", key=f"b_{prefix}_{p}_{cid}"):
                                df.at[idx, s_col] = 1 if is_s else 0
                                df.at[idx, m_col] = m_txt
                                save_data(df, CRM_FILE); st.rerun()

                # [상태 변경 버튼]
                c1, c2 = st.columns(2)
                if row['단계'] == "계약완료":
                    if c1.button("🚚 인도 완료", key=f"del_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = datetime.now().strftime('%Y-%m-%d')
                        save_data(df, CRM_FILE); st.rerun()
                    if c2.button("🚫 취소", key=f"can_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약취소"; save_data(df, CRM_FILE); st.rerun()
                elif row['단계'] == "계약취소":
                    if st.button("계약 복구", key=f"res_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약완료"; save_data(df, CRM_FILE); st.rerun()

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == '계약완료'], "con")
    with t_del: display_list(view_df[view_df['단계'] == '인도완료'], "del")
    with t_can: display_list(view_df[view_df['단계'] == '계약취소'], "can")
