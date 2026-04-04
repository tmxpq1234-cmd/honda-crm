import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (팀장님 정보 확인 완료) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"
GITHUB_TOKEN = "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"

# --- 2. 디자인 설정 (세련된 스타일) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 32px !important; font-weight: 700; color: #1a1a1a; margin-bottom: 5px; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 데이터 로드/저장 함수 (SHA 인증 자동화) ---
def get_github_data(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        info = res.json()
        content = base64.b64decode(info['content']).decode('utf-8-sig')
        return pd.read_csv(io.StringIO(content)).fillna(""), info['sha']
    return pd.DataFrame(), None

def save_to_github(df, path, message="Data Update"):
    # 저장 직전에 최신 SHA를 다시 따옵니다 (중요!)
    _, latest_sha = get_github_data(path)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    
    payload = {"message": message, "content": base64_content}
    if latest_sha:
        payload["sha"] = latest_sha
        
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code

# --- 4. 초기 데이터 로드 ---
if 'crm_df' not in st.session_state:
    df, _ = get_github_data(FILE_PATH)
    if df.empty: # 파일이 비어있을 경우 기본 컬럼 생성
        df = pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "1개월_발송", "1개월_메모", "3개월_발송", "3개월_메모", "6개월_발송", "6개월_메모", "12개월_발송", "12개월_메모", "비고"])
    st.session_state.crm_df = df

if 'user_df' not in st.session_state:
    udf, _ = get_github_data(USER_FILE)
    if udf.empty:
        udf = pd.DataFrame([{"ID": "박스테반", "Password": "1234"}, {"ID": "김태형", "Password": "2290"}, {"ID": "전유인", "Password": "2290"}, {"ID": "전명현", "Password": "2290"}, {"ID": "이준창", "Password": "2290"}])
    st.session_state.user_df = udf

# --- 5. 로그인 ---
user_db = dict(zip(st.session_state.user_df['ID'].astype(str), st.session_state.user_df['Password'].astype(str)))
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("사용자", list(user_db.keys()))
    p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 6. 메인 화면 ---
st.markdown(f'<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
with st.sidebar:
    st.write(f"**접속: {st.session_state.user_name}**")
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 데이터 새로고침"): st.session_state.clear(); st.rerun()

# --- 7. 팀장 도구 (인사관리/인수인계) ---
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리"):
        t1, t2 = st.tabs(["👥 인사 관리", "🔄 인수인계"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                new_n = st.text_input("신입 이름")
                if st.button("등록"):
                    st.session_state.user_df = pd.concat([st.session_state.user_df, pd.DataFrame([{"ID": new_n, "Password": "2290"}])], ignore_index=True)
                    save_to_github(st.session_state.user_df, USER_FILE); st.success("등록됨"); st.rerun()
        with t2:
            src = st.selectbox("기존 담당", list(user_db.keys()))
            tgt = st.selectbox("인수자", [u for u in user_db.keys() if u != src])
            target_ids = st.multiselect("고객 선택", options=st.session_state.crm_df[st.session_state.crm_df['담당자']==src].index.tolist(), format_func=lambda x: f"{st.session_state.crm_df.loc[x, '고객명']}")
            if st.button("인수인계 확정") and target_ids:
                st.session_state.crm_df.loc[target_ids, '담당자'] = tgt
                save_to_github(st.session_state.crm_df, FILE_PATH); st.success("완료"); st.rerun()

st.divider()

# --- 8. 고객 등록 및 사후관리 리스트 ---
col_reg, col_view = st.columns([1, 3])
with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_id = len(st.session_state.crm_df) + 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_to_github(st.session_state.crm_df, FILE_PATH)
                st.success(f"{name}님 저장 완료!"); st.rerun()

with col_view:
    tab_all, tab_post = st.tabs(["📊 현황 목록", "🚚 인도 및 사후관리"])
    df = st.session_state.crm_df
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    with tab_all:
        st.dataframe(view_df[view_df['단계'] != '계약취소'], use_container_width=True)

    with tab_post:
        target_post = view_df[view_df['단계'] == "인도완료"]
        for idx, row in target_post.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | {row['기준일']}"):
                # 사후관리 1, 3, 6, 12개월
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.write(f"**{p}개월**")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("발송", value=bool(row.get(s_col, 0)), key=f"s_{idx}_{p}")
                        m_txt = st.text_area("메모", value=row.get(m_col, ""), key=f"m_{idx}_{p}", height=70)
                        if st.button("저장", key=f"b_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col] = 1 if is_s else 0
                            st.session_state.crm_df.at[idx, m_col] = m_txt
                            save_to_github(st.session_state.crm_df, FILE_PATH); st.rerun()
