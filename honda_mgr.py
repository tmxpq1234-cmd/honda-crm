import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (Secrets 금고 연동 - 차단 방지) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"
# 💡 스트림릿 Secrets에 저장하신 키를 자동으로 가져옵니다.
GITHUB_TOKEN = st.secrets.get("github_token", "")

# --- 2. 디자인 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 30px !important; font-weight: 700; color: #1a1a1a; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        .stButton button { border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 깃허브 통신 함수 ---
def github_action(df, path):
    if not GITHUB_TOKEN:
        st.error("❌ Secrets에 'github_token'이 설정되지 않았습니다.")
        return 401
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    res_get = requests.get(url, headers=headers)
    sha = res_get.json().get('sha') if res_get.status_code == 200 else None
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    payload = {"message": f"Update {datetime.now()}", "content": base64_content}
    if sha: payload["sha"] = sha
    res_put = requests.put(url, headers=headers, json=payload)
    return res_put.status_code

def load_github_data(path):
    if not GITHUB_TOKEN: return pd.DataFrame()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
        return pd.read_csv(io.StringIO(content)).fillna("")
    return pd.DataFrame()

# --- 4. 데이터 초기 로드 ---
if 'crm_df' not in st.session_state:
    st.session_state.crm_df = load_github_data(FILE_PATH)
    if st.session_state.crm_df.empty:
        st.session_state.crm_df = pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "비고"])

if 'user_df' not in st.session_state:
    st.session_state.user_df = load_github_data(USER_FILE)
    if st.session_state.user_df.empty:
        st.session_state.user_df = pd.DataFrame([{"ID": "박스테반", "Password": "1234"}, {"ID": "김태형", "Password": "2290"}, {"ID": "전유인", "Password": "2290"}, {"ID": "전명현", "Password": "2290"}, {"ID": "이준창", "Password": "2290"}])

# --- 5. 로그인 ---
user_db = dict(zip(st.session_state.user_df['ID'].astype(str), st.session_state.user_df['Password'].astype(str)))
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">🚗 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("사용자 선택", list(user_db.keys())); p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p: st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 6. 헤더 및 사이드바 ---
st.markdown('<p class="main-header">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
with st.sidebar:
    st.write(f"🟢 **{st.session_state.user_name}** 접속 중")
    if st.button("🚪 로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 데이터 강제 새로고침"): st.session_state.clear(); st.rerun()

# --- 7. 팀장 도구 ---
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 설정"):
        t1, t2 = st.tabs(["👥 인사 관리", "🔄 업무 인수인계"])
        with t1:
            n_n = st.text_input("신입 이름"); n_p = st.text_input("비번", "2290")
            if st.button("신규 등록"):
                st.session_state.user_df = pd.concat([st.session_state.user_df, pd.DataFrame([{"ID": n_n, "Password": n_p}])], ignore_index=True)
                github_action(st.session_state.user_df, USER_FILE); st.success("등록됨"); st.rerun()

st.divider()

# --- 8. 메인 기능 레이아웃 ---
c_reg, c_view = st.columns([1, 3])
with c_reg:
    st.markdown('<div class="s-title">📍 신규 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("초기 단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": ""}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                github_action(st.session_state.crm_df, FILE_PATH); st.success("저장 완료!"); st.rerun()

with c_view:
    tab1, tab2, tab3 = st.tabs(["📝 계약 현황", "🚚 인도 완료 현황", "📅 사후관리 & 비고"])
    v_df = st.session_state.crm_df if st.session_state.user_name == "박스테반" else st.session_state.crm_df[st.session_state.crm_df['담당자'] == st.session_state.user_name]

    with tab1: # 계약 -> 인도 상태 변경 기능 복구
        con_df = v_df[v_df['단계'] == "계약완료"]
        if con_df.empty: st.info("현재 계약 상태인 고객이 없습니다.")
        for idx, row in con_df.iterrows():
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{row['고객명']}** ({row['모델']})")
            c2.write(f"담당: {row['담당자']} | {row['기준일']}")
            if c3.button("🚚 인도완료 처리", key=f"btn_{idx}"):
                st.session_state.crm_df.at[idx, '단계'] = "인도완료"
                st.session_state.crm_df.at[idx, '기준일'] = str(datetime.now().date())
                github_action(st.session_state.crm_df, FILE_PATH)
                st.success(f"{row['고객명']}님 인도 처리됨!"); st.rerun()
        st.divider()
        st.dataframe(con_df, use_container_width=True)

    with tab2: # 인도 완료 목록
        st.dataframe(v_df[v_df['단계'] == "인도완료"], use_container_width=True)

    with tab3: # 사후관리 기능
        care_df = v_df[v_df['단계'] == "인도완료"]
        for idx, row in care_df.iterrows():
            with st.expander(f"📌 {row['고객명']}님 사후관리 기록"):
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.write(f"**{p}개월**")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_내용"
                        is_s = st.checkbox("발송", value=bool(row.get(s_col, 0)), key=f"c_{idx}_{p}")
                        m_txt = st.text_area("메모", value=row.get(m_col, ""), key=f"t_{idx}_{p}", height=70)
                        if st.button("저장", key=f"b_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col] = 1 if is_s else 0
                            st.session_state.crm_df.at[idx, m_col] = m_txt
                            github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
                st.text_area("통합 비고", value=row.get('비고', ""), key=f"n_{idx}")
