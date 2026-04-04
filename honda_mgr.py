import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 앱 설정 ---
st.set_page_config(page_title="Honda CRM v13.0 Final", layout="wide")

# CSS 스타일 (팀장님이 좋아하시던 깔끔한 스타일)
st.markdown("""
    <style>
        .s-title { font-size: 22px !important; font-weight: bold; color: #CC0000; margin-bottom: 10px; }
        .stButton button { width: 100%; border-radius: 8px; }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 18px; font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1h5cEQQGrAIrrpU9qTik8PeUmpRE5zFyW2v1VVNP8e2w/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_crm_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl="0s")
def load_user_data(): return conn.read(spreadsheet=SHEET_URL, worksheet="Users", ttl="0s")
def save_crm_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
def save_user_data(df): conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=df)

# --- 3. 로그인 시스템 ---
try:
    user_df = load_user_data()
    user_db = dict(zip(user_df['ID'], user_df['Password']))
    curator_list = list(user_db.keys())
except Exception as e:
    st.error(f"⚠️ 사용자 데이터를 불러올 수 없습니다: {e}")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 Honda Korea CRM 접속")
    input_user = st.selectbox("사용자 선택", curator_list)
    input_pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if str(user_db.get(input_user)) == str(input_pw):
            st.session_state.logged_in = True
            st.session_state.user_name = input_user
            st.rerun()
        else: st.error("비밀번호를 확인해주세요.")
    st.stop()

# --- 4. 메인 데이터 로드 ---
df = load_crm_data()

# --- 5. 사이드바 (내 정보 및 로그아웃) ---
with st.sidebar:
    st.title(f"👤 {st.session_state.user_name} 팀장님")
    with st.expander("🔐 비밀번호 변경"):
        new_pw = st.text_input("새 비밀번호", type="password")
        if st.button("변경 저장"):
            user_df.loc[user_df['ID'] == st.session_state.user_name, 'Password'] = new_pw
            save_user_data(user_df); st.success("✅ 완료!"); st.rerun()
    st.divider()
    if st.button("🚪 로그아웃"):
        st.session_state.logged_in = False; st.rerun()

st.title("🚗 Honda 통합 고객 관리 시스템")

# --- 6. 팀장 전용 도구 (박스테반 팀장님만 보임) ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구"):
        m_tab1, m_tab2, m_tab3 = st.tabs(["🔍 필터", "👥 인사 관리", "🔄 업무 인계"])
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
            target_ids = st.multiselect("인계 고객 선택", options=df[df['담당자']==src].index.tolist(), format_func=lambda x: f"{df.loc[x, '고객명']}")
            if st.button("인계 실행") and target_ids:
                df.loc[target_ids, '담당자'] = tgt
                save_crm_data(df); st.success("인계 완료!"); st.rerun()

st.divider()

# --- 7. 메인 화면: 등록 및 리스트 ---
col_reg, col_view = st.columns([1, 2.8])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        date = st.date_input("기준일", datetime.now())
        if st.form_submit_button("시트에 저장"):
            if name:
                new_id = int(df['ID'].max()) + 1 if not df.empty else 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(date), "모델": mdl, "단계": step,
                           "1개월_발송": 0, "1개월_메모": "", "3개월_발송": 0, "3개월_메모": "",
                           "6개월_발송": 0, "6개월_메모": "", "12개월_발송": 0, "12개월_메모": "", "비고": ""}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_crm_data(df); st.success("등록 완료!"); st.rerun()

with col_view:
    t_all, t_con, t_del, t_can = st.tabs(["📊 전체", "📝 계약", "🚚 인도/사후관리", "🚫 취소"])
    
    view_df = df.copy()
    if st.session_state.user_name != "박스테반": view_df = view_df[view_df['담당자'] == st.session_state.user_name]
    elif selected_curator != "전체 보기": view_df = view_df[view_df['담당자'] == selected_curator]

    def display_list(target_df, prefix):
        for idx, row in target_df.iterrows():
            cid = row['ID']
            with st.expander(f"📌 [{row['단계']}] {row['고객명']} ({row['모델']}) - {row['담당자']}"):
                # 인도완료 시 사후관리 화면
                if row['단계'] == "인도완료":
                    st.write(f"📅 인도일: {row['기준일']}")
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
                
                # 계약완료 시 상태 변경
                if row['단계'] == "계약완료":
                    c1, c2 = st.columns(2)
                    if c1.button("🚚 인도 완료 처리", key=f"d_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "인도완료"; df.at[idx, '기준일'] = datetime.now().strftime('%Y-%m-%d')
                        save_crm_data(df); st.rerun()
                    if c2.button("🚫 계약 취소", key=f"c_{prefix}_{cid}"):
                        df.at[idx, '단계'] = "계약취소"; save_crm_data(df); st.rerun()

                # 비고 및 서류 링크 관리 (중요!)
                st.divider()
                note = st.text_area("비고 (드라이브 링크 등)", value=row['비고'] if pd.notna(row['비고']) else "", key=f"n_{prefix}_{cid}")
                if st.button("비고/링크 저장", key=f"nb_{prefix}_{cid}"):
                    df.at[idx, '비고'] = note
                    save_crm_data(df); st.success("시트 업데이트 완료!"); st.rerun()
                if pd.notna(row['비고']) and "http" in str(row['비고']):
                    st.link_button("📂 연결된 서류 보기", row['비고'], key=f"v_{prefix}_{cid}")

    with t_all: display_list(view_df[view_df['단계'] != '계약취소'], "all")
    with t_con: display_list(view_df[view_df['단계'] == '계약완료'], "con")
    with t_del: display_list(view_df[view_df['단계'] == '인도완료'], "del")
    with t_can: display_list(view_df[view_df['단계'] == '계약취소'], "can")
