import streamlit as st
import json
import os
from openai import OpenAI

# 1. 초기 설정 및 보안 체크
st.set_page_config(page_title="정처기 합격 메이커", layout="wide")

# 실행 파일의 절대 경로를 기준으로 설정 (이미지 경로 문제 해결용)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 접근 제한")
    password_input = st.text_input("서비스 이용을 위해 암호를 입력하세요", type="password")
    if st.button("로그인"):
        if password_input == st.secrets["LOGIN_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("암호가 올바르지 않습니다.")
    st.stop()

# 2. 데이터 로드 및 세션 상태 초기화
@st.cache_data
def load_data():
    if os.path.exists("exam_data.json"):
        with open("exam_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

exam_data = load_data()

if 'idx' not in st.session_state:
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.results = []  # [{id, result, user_choice, correct_ans}]
    st.session_state.submitted = False
    st.session_state.gpt_response = ""

# 3. GPT API 연동 함수
def ask_gpt_explanation(question, options, correct_answer):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    # options가 딕셔너리일 경우 문자열로 변환하여 전달
    opts_str = "\n".join([f"{k}: {v}" for k, v in options.items()])
    prompt = f"""
    정보처리기사 시험 문제에 대한 해설을 제공해줘.
    문제: {question}
    선택지:
    {opts_str}
    정답: {correct_answer}번
    이 문제가 왜 정답인지 초보자도 이해하기 쉽게 핵심 개념을 포함해서 설명해줘.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"GPT 연결 오류: {e}"

# 4. 결과 요약 페이지 (문제를 다 풀었을 때)
if st.session_state.idx >= len(exam_data):
    st.title("📊 학습 결과 요약")
    st.balloons()
    
    total_q = len(exam_data)
    score_pct = (st.session_state.score / total_q) * 100 if total_q > 0 else 0
    st.metric("최종 점수", f"{st.session_state.score} / {total_q}", f"{score_pct:.1f}%")
    
    st.write("### 문항별 정답 현황")
    cols = st.columns(5)
    for i, res in enumerate(st.session_state.results):
        with cols[i % 5]:
            color = "green" if res['result'] == "정답" else "red"
            st.markdown(f":{color}[Q{res['id']}: {res['result']}] (내 선택: {res['user_choice']}번)")

    if st.button("처음부터 다시 풀기"):
        st.session_state.idx = 0
        st.session_state.score = 0
        st.session_state.results = []
        st.rerun()
    st.stop()

# 5. 메인 문제 풀이 UI
q = exam_data[st.session_state.idx]

st.title("✍️ 정보처리기사 기출 풀이")
st.progress((st.session_state.idx + 1) / len(exam_data))

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader(f"Q{q['id']}. {q['question']}")
    
    # --- 이미지 경로 처리 로직 수정 ---
    if q.get('image'):
        # 1. 역슬래시(\\)를 현재 OS의 구분자에 맞게 변환
        normalized_path = os.path.normpath(q['image'])
        # 2. 실행 파일 위치를 기준으로 절대 경로 생성
        img_full_path = os.path.join(BASE_DIR, normalized_path)
        
        if os.path.exists(img_full_path):
            st.image(img_full_path, caption=f"문제 {q['id']} 관련 도식", use_container_width=False, width=500)
        else:
            st.warning(f"⚠️ 이미지를 찾을 수 없습니다: {normalized_path}")
    
    # 선지 구성 (JSON의 options 딕셔너리 값 사용)
    options_list = [f"{i+1}. {text}" for i, text in enumerate(q['options'].values())]
    user_choice = st.radio("보기에서 정답을 골라주세요", options_list, index=None, key=f"radio_{q['id']}")

    c1, c2 = st.columns([1, 4])
    with c1:
        submit_btn = st.button("정답 제출", use_container_width=True)
    with c2:
        if st.button("⚠️ 문제 오류 신고"):
            st.toast(f"{q['id']}번 문제 오류가 접수되었습니다.")

    if submit_btn or st.session_state.submitted:
        st.session_state.submitted = True
        if not user_choice:
            st.warning("정답을 먼저 선택하세요.")
        else:
            user_ans_num = int(user_choice.split('.')[0])
            correct_ans_num = int(q['answer'])
            
            if user_ans_num == correct_ans_num:
                st.success(f"✅ 정답입니다! (정답: {correct_ans_num}번)")
            else:
                st.error(f"❌ 오답입니다. 정답은 {correct_ans_num}번입니다.")
                
                # GPT 해설 요청 버튼
                if st.button("💡 GPT에게 해설 물어보기"):
                    with st.spinner("GPT가 해설을 작성 중입니다..."):
                        st.session_state.gpt_response = ask_gpt_explanation(q['question'], q['options'], correct_ans_num)
                
                if st.session_state.gpt_response:
                    st.info(f"**GPT AI 해설:**\n\n{st.session_state.gpt_response}")

    # 다음 문제 버튼 (제출 후에만 표시)
    if st.session_state.submitted and user_choice:
        if st.button("다음 문제 ➡️"):
            user_val = int(user_choice.split('.')[0])
            correct_val = int(q['answer'])
            is_correct = (user_val == correct_val)
            
            st.session_state.results.append({
                "id": q['id'],
                "result": "정답" if is_correct else "오답",
                "user_choice": user_val,
                "correct_ans": correct_val
            })
            if is_correct:
                st.session_state.score += 1
            
            # 상태 초기화 및 인덱스 증가
            st.session_state.idx += 1
            st.session_state.submitted = False
            st.session_state.gpt_response = ""
            st.rerun()

with col_side:
    st.write("### 학습 정보")
    st.write(f"- **현재 문항:** {st.session_state.idx + 1} / {len(exam_data)}")
    st.write(f"- **맞힌 개수:** {st.session_state.score}")
    
    if st.button("학습 종료 및 결과 보기"):
        st.session_state.idx = len(exam_data)
        st.rerun()
