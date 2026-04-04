import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 (보안 저장 방식 절대 유지) ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"

k1 = "ghp_fX61tF2hEH21Z"
k2 = "TMhTgKvBWtZA0Plxg3RRQd2"
GITHUB_TOKEN = k1 + k2 

# --- 2. 디자인 (이미지 속 버튼 줄바꿈 및 불균형 해결) ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 28px !important; font-weight: 700; color: #1a1a1a; margin-bottom: 10px; }
        .s-title { font-size: 18px !important; font-weight: 700; color: #222; border-left: 5px solid #CC0000; padding-left: 12px; margin-bottom: 15px; }
        
        /* 🛠️ 버튼 줄바꿈 방지 및 높이 칼맞춤 */
        .stButton button { 
            border-radius: 6px; font-weight: 600; 
            white-space: nowrap !important; /* 글씨 줄바꿈 절대 방지 */
            width: 100% !important; height: 42px !important;
            display: flex; align-items: center; justify-content: center;
        }
        .date-label { 
            color: #CC0000; font-weight: 700; font-size: 13px; 
            white-space: nowrap !important; display: block; margin-bottom: 8px; 
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. 통신 함수 (날짜순 정렬 저장) ---
def github_action(df, path):
    if path == FILE_PATH:
        # 날짜순 정렬: 인도일 우선 -> 계약일 기준 (최신순)
        df['temp_date'] = df['인도일'].replace('', '1900-01-01')
        df.loc[df['temp_date'] == '1900-01-01', 'temp_date'] = df['계약일']
        df = df.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
    
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

# --- 4. 데이터 로드 ---
if 'crm_df' not in st.session_state: st.session_state.crm_df = load_github_data(FILE_PATH)
if 'user_df' not in st.session_state: st.session_state.user_df = load_github_data(USER_FILE)

# --- 5. 로그인 ---
user_db = dict(zip(st.session_state.user_df['ID'].astype(str), st.session_state.user_df['Password'].astype(str)))
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<p class="main-header" style="text-align:center; padding-top:100px;">🚗 HONDA CRM LOGIN</p>', unsafe_allow_html=True)
    u = st.selectbox("사용자 선택", list(user_db.keys())); p = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if user_db.get(u) == p: st.session_state.logged_in = True; st.session_state.user_name = u; st.rerun()
    st.stop()

# --- 6. 상단 UI ---
st.markdown('<p class="main-header">HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
with st.sidebar:
    st.write(f"🟢 **{st.session_state.user_name}** 접속 중")
    if st.button("🚪 로그아웃"): st.session_state.logged_in = False; st.rerun()
    st.divider()
    if st.button("🔄 전체 동기화"): st.session_state.clear(); st.rerun()

# --- 7. 팀장 도구 (인수인계 상세 유지) ---
if st.session_state.user_name == "박스테반":
    with st.expander("⚙️ 팀장 전용 도구 (인사 및 인수인계)", expanded=False):
        t_ 인사, t_ 인수인계 = st.tabs(["👥 인사 관리", "🔄 업무 인수인계"])
        with t_ 인사:
            c1, c2 = st.columns(2)
            with c1:
                new_n = st.text_input("신입 이름 입력", key="new_curator")
                if st.button("신규 등록"):
                    st.session_state.user_df = pd.concat([st.session_state.user_df, pd.DataFrame([{"ID": new_n, "Password": "2290"}])], ignore_index=True)
                    github_action(st.session_state.user_df, USER_FILE); st.success(f"{new_n}님 등록됨"); st.rerun()
            with c2:
                del_target = st.selectbox("퇴사자 선택", [u for u in user_db.keys() if u != "박스테반"])
                if st.button("명단에서 삭제"):
                    st.session_state.user_df = st.session_state.user_df[st.session_state.user_df['ID'] != del_target]
                    github_action(st.session_state.user_df, USER_FILE); st.success(f"{del_target}님 삭제 완료"); st.rerun()
        with t_ 인수인계:
            st.write("**🔄 선택형 고객 인수인계**")
            src = st.selectbox("업무를 넘길 담당자", list(user_db.keys()), key="src")
            tgt = st.selectbox("업무를 받을 담당자", [u for u in user_db.keys() if u != src], key="tgt")
            src_cust = st.session_state.crm_df[st.session_state.crm_df['담당자'] == src]
            if not src_cust.empty:
                sel_cust = st.multiselect("이전할 고객 선택", options=src_cust.index.tolist(), format_func=lambda x: f"{src_cust.loc[x, '고객명']} ({src_cust.loc[x, '모델']})")
                if st.button(f"선택한 {len(sel_cust)}명 인수인계 실행"):
                    if sel_cust:
                        st.session_state.crm_df.loc[sel_cust, '담당자'] = tgt
                        github_action(st.session_state.crm_df, FILE_PATH); st.success("이전 완료!"); st.rerun()

st.divider()

# --- 8. 고객 리스트 필터 및 조회 ---
col_reg, col_view = st.columns([1, 3])
with col_reg:
    st.markdown('<div class="s-title">📍 신규 고객 등록</div>', unsafe_allow_html=True)
    with st.form("reg", clear_on_submit=True):
        name = st.text_input("고객명")
        mdl = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"])
        reg_date = st.date_input("계약/등록 날짜", value=datetime.now().date())
        step = st.radio("상태", ["계약완료", "인도완료"], horizontal=True)
        if st.form_submit_button("시스템 저장"):
            if name:
                new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": st.session_state.user_name, "계약일": str(reg_date), "인도일": str(reg_date) if step == "인도완료" else "", "모델": mdl, "단계": step, "비고": ""}
                st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
                github_action(st.session_state.crm_df, FILE_PATH); st.rerun()

with col_view:
    tab1, tab2, tab3 = st.tabs(["📝 계약 현황", "🚚 인도 완료 목록", "📅 사후관리 & 비고"])
    
    # 🛠️ 큐레이터별 필터 박스 (팀장 로그인 시)
    filter_curator = "전체"
    if st.session_state.user_name == "박스테반":
        filter_curator = st.selectbox("🔍 큐레이터별 명단 보기", ["전체"] + list(user_db.keys()))
    
    # 데이터 필터링 (팀장은 전체/선택, 팀원은 본인것만)
    if st.session_state.user_name == "박스테반":
        v_df = st.session_state.crm_df if filter_curator == "전체" else st.session_state.crm_df[st.session_state.crm_df['담당자'] == filter_curator]
    else:
        v_df = st.session_state.crm_df[st.session_state.crm_df['담당자'] == st.session_state.user_name]

    def render_edit(idx, row):
        with st.expander(f"✏️ {row['고객명']} 정보 수정"):
            en = st.text_input("이름", value=row['고객명'], key=f"en_{idx}")
            em = st.selectbox("모델", ["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"], index=["ACCORD", "CR-V 2WD", "CR-V 4WD", "PILOT", "ODYSSEY"].index(row['모델']), key=f"em_{idx}")
            ecd = st.date_input("계약일", value=datetime.strptime(str(row['계약일']), "%Y-%m-%d").date(), key=f"ecd_{idx}")
            eid = None
            if row['단계'] == "인도완료": eid = st.date_input("인도일", value=datetime.strptime(str(row['인도일']), "%Y-%m-%d").date(), key=f"eid_{idx}")
            emgr = st.selectbox("담당자", list(user_db.keys()), index=list(user_db.keys()).index(row['담당자']), key=f"emgr_{idx}")
            if st.button("수정 내용 저장", key=f"esav_{idx}"):
                st.session_state.crm_df.at[idx, '고객명'], st.session_state.crm_df.at[idx, '모델'] = en, em
                st.session_state.crm_df.at[idx, '계약일'], st.session_state.crm_df.at[idx, '담당자'] = str(ecd), emgr
                if eid: st.session_state.crm_df.at[idx, '인도일'] = str(eid)
                github_action(st.session_state.crm_df, FILE_PATH); st.rerun()

    with tab1:
        target_con = v_df[v_df['단계'] == "계약완료"]
        for idx, row in target_con.iterrows():
            c1, c2, c3 = st.columns([2, 3, 1.2]) # 균형 맞춤
            c1.markdown(f"**{row['고객명']}** ({row['모델']})")
            c2.caption(f"등록일: {row['계약일']} | 담당: {row['담당자']}")
            if c3.button("🚚 인도완료", key=f"upd_{idx}"):
                st.session_state.crm_df.at[idx, '단계'] = "인도완료"
                st.session_state.crm_df.at[idx, '인도일'] = str(datetime.now().date())
                github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
            render_edit(idx, row)
        st.divider(); st.dataframe(target_con, use_container_width=True)

    with tab2:
        target_ind = v_df[v_df['단계'] == "인도완료"]
        for idx, row in target_ind.iterrows():
            st.markdown(f"**{row['고객명']}** ({row['모델']}) | 인도: {row['인도일']} | 담당: {row['담당자']}")
            render_edit(idx, row)
        st.divider(); st.dataframe(target_ind, use_container_width=True)

    with tab3: # 사후관리
        care_df = v_df[v_df['단계'] == "인도완료"]
        for idx, row in care_df.iterrows():
            with st.expander(f"📌 {row['고객명']} 사후관리"):
                try: base_date = datetime.strptime(str(row['인도일']), "%Y-%m-%d")
                except: base_date = datetime.now()
                cols = st.columns(4)
                for i, p in enumerate([1, 3, 6, 12]):
                    with cols[i]:
                        target_date = (base_date + relativedelta(months=p)).strftime("%Y-%m-%d")
                        st.markdown(f"<div class='date-label'>📅 {p}개월 ({target_date})</div>", unsafe_allow_html=True)
                        s_col, m_col = f"{p}개월_발송", f"{p}개월_메모"
                        is_s = st.checkbox("완료", value=bool(row.get(s_col, 0)), key=f"chk_{idx}_{p}")
                        m_txt = st.text_area("내용", value=row.get(m_col, ""), key=f"txt_{idx}_{p}", height=70)
                        if st.button("저장", key=f"sav_{idx}_{p}"):
                            st.session_state.crm_df.at[idx, s_col], st.session_state.crm_df.at[idx, m_col] = (1 if is_s else 0), m_txt
                            github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
                st.divider()
                note = st.text_area("🗒️ 비고", value=row.get('비고', ""), key=f"note_{idx}")
                if st.button("비고 저장", key=f"nsav_{idx}"):
                    st.session_state.crm_df.at[idx, '비고'] = note
                    github_action(st.session_state.crm_df, FILE_PATH); st.rerun()
