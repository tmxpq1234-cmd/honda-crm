import streamlit as st
import pandas as pd
import requests
import base64
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 설정 ---
GITHUB_REPO = "tmxpq1234-cmd/honda-crm"
FILE_PATH = "crm_data.csv"
USER_FILE = "users.csv"
# 💡 여기에 방금 복사한 번호를 따옴표 안에 붙여넣으세요!
GITHUB_TOKEN = "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"

# --- 2. 디자인 ---
st.set_page_config(page_title="HONDA CRM", layout="wide")
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif !important; }
        .main-header { font-size: 28px !important; font-weight: 700; color: #1a1a1a; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 저장 함수 (SHA 자동 처리) ---
def github_action(df, path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res_get = requests.get(url, headers=headers)
    sha = res_get.json().get('sha') if res_get.status_code == 200 else None
    
    csv_content = df.to_csv(index=False, encoding='utf-8-sig')
    base64_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    payload = {"message": f"Update {datetime.now()}", "content": base64_content}
    if sha: payload["sha"] = sha
    res_put = requests.put(url, headers=headers, json=payload)
    return res_put.status_code

# --- 데이터 로드 및 앱 시작 ---
if 'crm_df' not in st.session_state:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if res.status_code == 200:
        content = base64.b64decode(res.json()['content']).decode('utf-8-sig')
        st.session_state.crm_df = pd.read_csv(io.StringIO(content)).fillna("")
    else:
        st.session_state.crm_df = pd.DataFrame(columns=["ID", "고객명", "담당자", "기준일", "모델", "단계", "비고"])

# --- (이하 고객 등록 및 리스트 코드는 동일합니다) ---
st.markdown('<p class="main-header">🚗 HONDA 통합 고객 관리 시스템</p>', unsafe_allow_html=True)
name = st.text_input("신규 고객명")
if st.button("시스템 저장"):
    new_row = {"ID": len(st.session_state.crm_df)+1, "고객명": name, "담당자": "박스테반", "기준일": str(datetime.now().date()), "모델": "ACCORD", "단계": "계약완료"}
    st.session_state.crm_df = pd.concat([st.session_state.crm_df, pd.DataFrame([new_row])], ignore_index=True).fillna("")
    status = github_action(st.session_state.crm_df, FILE_PATH)
    if status in [200, 201]: st.success("✅ 깃허브 저장 성공!"); st.rerun()
    else: st.error(f"❌ 실패 (코드 {status})")

st.dataframe(st.session_state.crm_df, use_container_width=True)
