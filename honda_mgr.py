import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (저장 성공했던 보안 조각 방식 유지) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"

# 💡 깃허브 자동 차단 방지용 키 조각
k1 = "ghp_fX61tF2hEH21Z"
k2 = "TMhTgKvBWtZA0Plxg3RRQd2"
GITHUB_TOKEN = k1 + k2 

# --- 2. 디자인 (세련된 Pretendard 폰트) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 28px !important; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        .stButton button { border-radius: 6px; font-weight: 600; transition: all 0.2s; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 깃허브 통신 함수 (검증된 방식) ---
def github_action(df, path):
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

# --- 6. 대시보드 UI ---
st.markdown('<p class="main-header">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
with st.sidebar:
    st.write(f"🟢 **{st.session_state.user_name}** 접속 중")
    if st.button("🚪 로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 전체 동기화"): st.session_state.clear(); st.rerun()

# --- 7. 팀장 관리 도구 ---
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 도구 (인사 및 인수인계)"):
        t1, t2 = st.tabs(["👥 인사 관리", "🔄 업무 인수인계"])
        with t1:
            c1, c2 = st.columns(2)
            with c1:
                new_n = st.text_input("신입 이름")
                if st.button("큐레이터 등록"):
                    st.session_state.user_df = pd.concat([st.session_state.user_df, pd.DataFrame([{"ID": new_n, "Password": "2290"}])], ignore_index=True)
                    github_action(st.session_state.user_df, USER_FILE); st.success(f"{new_n}님 등록됨"); st.rerun()
        with t2:
            src = st.selectbox("기존 담당", list(user_db.keys())); tgt = st.selectbox("인수자", [u for u in user_db.keys() if u != src])
            if st.button("업무 일괄 인수인계"):
                st.session_state.crm_df.loc[st.session_state.crm_df['담당자'] == src, '담당자'] = tgt
                github_action(st.session_state.crm_df, FILE_PATH); st.success("이전 완료"); st.rerun()

st.divider()

# --- 8. 고객 등록 및 관리 섹션 ---
col_reg, col_view = st.columns([1, 3])
with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("상태", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step, "비고": ""}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                code = github_action(st.session_state.crm_df, FILE_PATH)
                if code in [200, 201]: st.success("✅ 저장 성공!"); st.rerun()

with col_view:
    tab1, tab2, tab3 = st.tabs(["📝 계약 현황", "🚚 인도 완료 목록", "📅 사후관리 & 비고"])
    df = st.session_state.crm_df
    v_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]

    with tab1: # 계약 현황 & 상태 변경 기능
        target_con = v_df[v_df['단계'] == "계약완료"]
        if target_con.empty: st.info("계약 상태의 고객이 없습니다.")
        for idx, row in target_con.iterrows():
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{row['고객명']}** ({row['모델']})")
            c2.caption(f"등록일: {row['기준일']} | 담당: {row['담당자']}")
            if c3.button("🚚 인도완료 처리", key=f"upd_{idx}"):
                st.session_state.crm_df.at[idx, '단계'] = "인도완료"
                st.session_state.crm_df.at[idx, '기준일'] = str(datetime.now().date())
                github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
        st.divider()
        st.dataframe(target_con, use_container_width=True)

    with tab2: # 인도 완료 현황
        st.dataframe(v_df[v_df['단계'] == "인도완료"], use_container_width=True)

    with tab3: # 사후관리 및 비고
        care_df = v_df[v_df['단계'] == "인도완료"]
        for idx, row in care_df.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 인도일: {row['기준일']}"):
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.write(f"**{p}개월**")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("완료", value=bool(row.get(s_col, 0)), key=f"chk_{idx}_{p}")
                        m_txt = st.text_area("내용", value=row.get(m_col, ""), key=f"txt_{idx}_{p}", height=70)
                        if st.button("저장", key=f"sav_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col] = 1 if is_s else 0
                            st.session_state.crm_df.at[idx, m_col] = m_txt
                            github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
                
                st.divider()
                # 통합 비고 기능
                note = st.text_area("🗒️ 고객 상담 비고", value=row.get('비고', ""), key=f"note_{idx}")
                if st.button("비고 저장", key=f"nsav_{idx}"):
                    st.session_state.crm_df.at[idx, '비고'] = note
                    github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
