import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (팀장님 정보 직접 매립) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"
GITHUB_TOKEN = "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"

# --- 2. 디자인 (Pretendard 서체 적용 및 깔끔한 레이아웃) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 28px !important; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 깃허브 통신 함수 (SHA 인증 자동화 보강) ---
def github_action(df, path, message="Update CRM Data"):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 1. 최신 SHA 번호를 깃허브에서 직접 가져옴
    res_get = requests.get(url, headers=headers)
    sha = res_get.json().get('sha') if res_get.status_code == 200 else None
    
    # 2. 데이터를 CSV 포맷으로 변환
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    
    # 3. 깃허브에 덮어쓰기 요청
    payload = {"message": message, "content": base64_content}
    if sha: payload["sha"] = sha
        
    res_put = requests.put(url, headers=headers, json=payload)
    return res_put.status_code

def load_github_data(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
        return pd.read_csv(io.StringIO(content)).fillna("")
    return pd.DataFrame()

# --- 4. 데이터 초기 로드 ---
if 'crm_df' not in st.session_state:
    df = load_github_data(FILE_PATH)
    if df.empty:
        df = pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "비고"])
    st.session_state.crm_df = df

if 'user_df' not in st.session_state:
    udf = load_github_data(USER_FILE)
    if udf.empty:
        udf = pd.DataFrame([{"ID": "박스테반", "Password": "1234"}, {"ID": "김태형", "Password": "2290"}, {"ID": "전유인", "Password": "2290"}, {"ID": "전명현", "Password": "2290"}, {"ID": "이준창", "Password": "2290"}])
    st.session_state.user_df = udf

# --- 5. 로그인 로직 ---
user_db = dict(zip(st.session_state.user_df['ID'].astype(str), st.session_state.user_df['Password'].astype(str)))
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">HONDA CRM ACCESS</p>', unsafe_allow_html=True)
    u = st.selectbox("사용자 선택", list(user_db.keys()))
    p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 6. 메인 화면 ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)

with st.sidebar:
    st.write(f"**현재 접속: {st.session_state.user_name}**")
    if st.button("🚪 로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 전체 데이터 새로고침"): 
        st.session_state.clear()
        st.rerun()

# --- 7. 팀장 전용 도구 ---
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 인사 관리 및 필터", expanded=False):
        t1, t2 = st.tabs(["👥 인사 관리", "🔍 필터"])
        with t1:
            new_n = st.text_input("추가할 큐레이터 성함")
            if st.button("큐레이터 등록"):
                st.session_state.user_df = pd.concat([st.session_state.user_df, pd.DataFrame([{"ID": new_n, "Password": "2290"}])], ignore_index=True)
                github_action(st.session_state.user_df, USER_FILE)
                st.success(f"{new_n}님 등록 완료"); st.rerun()

st.divider()

# --- 8. 고객 등록 및 현황 목록 ---
col_reg, col_view = st.columns([1, 3])
with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("customer_reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("상태", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템에 저장"):
            if name:
                new_id = len(st.session_state.crm_df) + 1
                new_row = {"ID": new_id, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step}
                # 세션에 임시 저장 후 즉시 깃허브 전송
                temp_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                st.session_state.crm_df = temp_df
                
                status = github_action(st.session_state.crm_df, FILE_PATH)
                if status in [200, 201]:
                    st.success(f"✅ {name}님 데이터가 깃허브에 안전하게 저장되었습니다!")
                    st.rerun()
                else:
                    st.error(f"❌ 저장 실패 (에러코드: {status}). 토큰 권한을 확인하세요.")

with col_view:
    tab_list, tab_care = st.tabs(["📊 전체 현황", "🚚 인도 및 사후관리"])
    df = st.session_state.crm_df
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    with tab_list:
        st.dataframe(view_df[view_df['단계'] != '계약취소'], use_container_width=True)

    with tab_care:
        care_df = view_df[view_df['단계'] == "인도완료"]
        if care_df.empty: st.info("인도 완료된 고객이 없습니다.")
        for idx, row in care_df.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 인도일: {row['기준일']}"):
                # 1, 3, 6, 12개월 사후관리 칸 복구
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.write(f"**{p}개월**")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("발송", value=bool(row.get(s_col, 0)), key=f"check_{idx}_{p}")
                        m_txt = st.text_area("내용", value=row.get(m_col, ""), key=f"memo_{idx}_{p}", height=70)
                        if st.button("기록 저장", key=f"save_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col] = 1 if is_s else 0
                            st.session_state.crm_df.at[idx, m_col] = m_txt
                            github_action(st.session_state.crm_df, FILE_PATH)
                            st.rerun()
