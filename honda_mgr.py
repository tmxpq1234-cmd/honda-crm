import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (팀장님 토큰 및 저장소 직접 매립) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"
# 💡 팀장님이 주신 토큰을 코드에 직접 넣었습니다. 이제 Secrets 설정 없이도 작동합니다!
GITHUB_TOKEN = "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"

# --- 2. 세련된 디자인 설정 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 32px !important; font-weight: 700; color: #1a1a1a; margin-bottom: 5px; letter-spacing: -1px; }
        .sub-header { font-size: 14px; color: #666; margin-bottom: 25px; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        .stButton button { border-radius: 6px; font-weight: 600; transition: all 0.2s; }
        .stButton button:hover { background-color: #CC0000 !important; color: white !important; border-color: #CC0000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 데이터 로드/저장 함수 (GitHub API) ---
def load_github_file(path):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
            return pd.read_csv(io.StringIO(content)).fillna(""), res.json()['sha']
    except: pass
    return pd.DataFrame(), None

def save_github_file(df, path, sha, message="Update CRM Data"):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    payload = {"message": message, "content": base64_content, "sha": sha}
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code

# --- 4. 초기 데이터 로드 ---
if 'crm_df' not in st.session_state:
    df, sha = load_github_file(FILE_PATH)
    st.session_state.crm_df, st.session_state.crm_sha = df, sha
    udf, usha = load_github_file(USER_FILE)
    st.session_state.user_df, st.session_state.user_sha = udf, usha

# --- 5. 로그인 시스템 ---
user_db = dict(zip(st.session_state.user_df['ID'].astype(str), st.session_state.user_df['Password'].astype(str)))
curator_list = list(user_db.keys())

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">HONDA CRM ACCESS</p>', unsafe_allow_html=True)
    u = st.selectbox("사용자 선택", curator_list if curator_list else ["박스테반"])
    p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p:
            st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
        else: st.error("비밀번호를 확인해주세요.")
    st.stop()

# --- 6. 메인 화면 레이아웃 ---
st.markdown('<p class="main-header">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">관리자: {st.session_state.user_name}</p>', unsafe_allow_html=True)

with st.sidebar:
    if st.button("🚪 로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 최신 데이터 동기화"): 
        df, sha = load_github_file(FILE_PATH)
        st.session_state.crm_df, st.session_state.crm_sha = df, sha
        st.success("동기화 완료!"); st.rerun()

# --- 7. 팀장 전용 도구 (박스테반 전용) ---
selected_curator = "전체 보기"
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 관리 도구", expanded=False):
        m_tab1, m_tab2, m_tab3 = st.tabs(["🔍 필터", "👥 인사 관리", "🔄 인수인계"])
        with m_tab1: selected_curator = st.selectbox("조회 담당자", ["전체 보기"] + curator_list)
        with m_tab2:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                new_n = st.text_input("신입 이름")
                if st.button("✨ 신입 등록"):
                    new_user = pd.DataFrame([{"ID": new_n, "Password": "2290"}])
                    st.session_state.user_df = pd.concat([st.session_state.user_df, new_user], ignore_index=True)
                    save_github_file(st.session_state.user_df, USER_FILE, st.session_state.user_sha)
                    st.success(f"{new_n} 등록됨"); st.rerun()
            with c_col2:
                del_n = st.selectbox("퇴사자 삭제", [c for c in curator_list if c != "박스테반"])
                if st.button("🗑️ 삭제 실행"):
                    st.session_state.user_df = st.session_state.user_df[st.session_state.user_df['ID'] != del_n]
                    save_github_file(st.session_state.user_df, USER_FILE, st.session_state.user_sha)
                    st.rerun()
        with m_tab3:
            src = st.selectbox("기존 담당", curator_list); tgt = st.selectbox("인수자", [c for c in curator_list if c != src])
            target_ids = st.multiselect("고객 선택", options=st.session_state.crm_df[st.session_state.crm_df['담당자']==src].index.tolist(), format_func=lambda x: f"{st.session_state.crm_df.loc[x, '고객명']}")
            if st.button("인수인계 실행") and target_ids:
                st.session_state.crm_df.loc[target_ids, '담당자'] = tgt
                save_github_file(st.session_state.crm_df, FILE_PATH, st.session_state.crm_sha); st.rerun()

st.divider()

# --- 8. 고객 등록 및 사후관리 ---
col_reg, col_view = st.columns([1, 3])

with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        step = st.radio("단계", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": st.session_state.user_name, "기준일": str(datetime.now().date()), "모델": mdl, "단계": step}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                save_github_file(st.session_state.crm_df, FILE_PATH, st.session_state.crm_sha)
                st.success(f"{name} 등록 완료!"); st.rerun()

with col_view:
    t_all, t_del = st.tabs(["📊 현황 목록", "🚚 인도 및 사후관리"])
    df = st.session_state.crm_df
    view_df = df if st.session_state.user_name == "박스테반" else df[df['담당자'] == st.session_state.user_name]
    if selected_curator != "전체 보기": view_df = view_df[view_df['담당자'] == selected_curator]

    with t_all:
        st.dataframe(view_df[view_df['단계'] != '계약취소'], use_container_width=True)

    with t_del:
        target_del = view_df[view_df['단계'] == "인도완료"]
        if target_del.empty: st.info("인도 완료된 고객이 없습니다.")
        for idx, row in target_del.iterrows():
            with st.expander(f"📌 {row['고객명']} ({row['모델']}) | 인도일: {row['기준일']}"):
                # 사후관리 1, 3, 6, 12개월 완벽 복구
                base_d = datetime.strptime(str(row['기준일']), '%Y-%m-%d')
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        st.markdown(f"**{p}개월 차**")
                        st.caption(f"📅 {(base_d + relativedelta(months=p)).strftime('%m/%d')}")
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("발송완료", value=bool(row.get(s_col, 0)), key=f"s_{idx}_{p}")
                        m_txt = st.text_area("메시지 내용", value=row.get(m_col, ""), key=f"m_{idx}_{p}", height=80)
                        if st.button("저장", key=f"b_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col] = 1 if is_s else 0
                            st.session_state.crm_df.at[idx, m_col] = m_txt
                            save_github_file(st.session_state.crm_df, FILE_PATH, st.session_state.crm_sha)
                            st.success("기록 저장됨"); st.rerun()
                
                st.divider()
                note = st.text_area("🗒️ 전체 비고", value=row.get('비고', ""), key=f"note_{idx}")
                if st.button("비고 저장", key=f"nb_{idx}"):
                    st.session_state.crm_df.at[idx, '비고'] = note
                    save_github_file(st.session_state.crm_df, FILE_PATH, st.session_state.crm_sha); st.rerun()
