import streamlit as st
import json
import os
import plotly.express as px
from openai import OpenAI

# 1. 초기 설정 및 보안 체크
st.set_page_config(page_title="NEMO GAME", layout="wide")

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 접근 제한")
    password_input = st.text_input("서비스 이용을 위해 암호를 입력하세요. made by luke park", type="password")
    if st.button("로그인"):
        # 스트림릿 secrets에 설정된 LOGIN_PASSWORD와 비교
        if password_input == st.secrets["LOGIN_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("누구십니까?????? 암호가 올바르지 않습니다.")
    st.stop()

# 2. 데이터 로드 함수 및 회차 매핑
exam_files = {
    "<2016년 1회차>": "2016_03.json",
    "2016년 2회차": "2016_05.json",
    "<2020년 1회차>": "2020_06.json",
    "2020년 2회차": "2020_08.json",
    "2020년 3회차": "2020_09.json",
    "<2021년 1회차>": "2021_03.json",
    "2021년 2회차": "2021_05.json",
    "2021년 3회차": "2021_08.json",
    "<2022년 1회차>": "2022_03.json",
    "2022년 2회차": "2022_04.json" # 사용자의 요청에 따른 추가
}

@st.cache_data
def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 사이드바에서 회차 선택
selected_exam_name = st.sidebar.selectbox("📅 풀이할 회차를 선택하세요", list(exam_files.keys()))
selected_file = exam_files[selected_exam_name]

# 회차가 변경되면 세션 상태 초기화
if "current_exam" not in st.session_state or st.session_state.current_exam != selected_exam_name:
    st.session_state.current_exam = selected_exam_name
    st.session_state.idx = 0
    st.session_state.score = 0
    st.session_state.results = []
    st.session_state.submitted = False
    st.session_state.gpt_response = ""

exam_data = load_data(selected_file)

# 데이터가 비어있을 경우 예외 처리
if not exam_data:
    st.error(f"⚠️ {selected_file} 파일을 찾을 수 없습니다. 파일 경로를 확인하세요.")
    st.stop()

# 3. GPT API 연동 함수
def ask_gpt_explanation(question, options, correct_answer):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
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

# 4. 결과 요약 페이지
if st.session_state.idx >= len(exam_data):
    st.title(f"📊 {st.session_state.current_exam} 학습 결과 요약")
    st.balloons()
    
    total_q = len(exam_data)
    score_pct = (st.session_state.score / total_q) * 100 if total_q > 0 else 0
    st.metric("최종 점수", f"{st.session_state.score} / {total_q}", f"{score_pct:.1f}%")
    
    st.write("### 문항별 정답 현황")
    cols = st.columns(5)
    for i, res in enumerate(st.session_state.results):
        with cols[i % 5]:
            color = "green" if res['result'] == "정답" else "red"
            st.markdown(f":{color}[Q{res['id']}: {res['result']}]")

    if st.button("처음부터 다시 풀기"):
        st.session_state.idx = 0
        st.session_state.score = 0
        st.session_state.results = []
        st.session_state.submitted = False
        st.rerun()
    st.stop()

# 5. 메인 문제 풀이 UI
q = exam_data[st.session_state.idx]

st.title(f"📚 NEMO GAME")
st.progress((st.session_state.idx + 1) / len(exam_data))

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader(f"Q{q['id']}. {q['question']}")
    
    if q.get('image'):
        rel_img_path = q['image'].replace('\\', '/')
        if os.path.exists(rel_img_path):
            st.image(rel_img_path, caption=f"문제 {q['id']} 관련 도식", width=500)
        else:
            st.warning(f"⚠️ 이미지를 찾을 수 없습니다: {rel_img_path}")
    
    # 선지 구성
    options_list = [f"{i+1}. {text}" for i, text in enumerate(q['options'].values())]
    user_choice = st.radio("보기에서 정답을 골라주세요", options_list, index=None, key=f"radio_{selected_exam_name}_{st.session_state.idx}")

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
                if st.button("💡 GPT에게 해설 물어보기"):
                    with st.spinner("GPT가 해설을 작성 중입니다..."):
                        st.session_state.gpt_response = ask_gpt_explanation(q['question'], q['options'], correct_ans_num)
                
                if st.session_state.gpt_response:
                    st.info(f"**GPT AI 해설:**\n\n{st.session_state.gpt_response}")

    if st.session_state.submitted and user_choice:
        if st.button("다음 문제 ➡️"):
            user_val = int(user_choice.split('.')[0])
            correct_val = int(q['answer'])
            is_correct = (user_val == correct_val)
            
            st.session_state.results.append({
                "id": q['id'],
                "result": "정답" if is_correct else "오답",
                "user_choice": user_val
            })
            if is_correct:
                st.session_state.score += 1
            
            st.session_state.idx += 1
            st.session_state.submitted = False
            st.session_state.gpt_response = ""
            st.rerun()

# 6. 사이드바 - 실시간 학습 정보 및 파이차트
with col_side:
    st.write("### 📊 실시간 학습 현황")
    
    answered_count = len(st.session_state.results)
    correct_count = st.session_state.score
    incorrect_count = answered_count - correct_count
    
    if answered_count > 0:
        # 차트 데이터 준비
        df_pie = {"상태": ["정답", "오답"], "개수": [correct_count, incorrect_count]}
        
        # 파이차트 생성
        fig = px.pie(
            df_pie, values="개수", names="상태", hole=0.4,
            color="상태", color_discrete_map={"정답": "#28a745", "오답": "#dc3545"}
        )
        fig.update_layout(showlegend=True, margin=dict(l=10, r=10, t=10, b=10), height=250)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("문제를 풀면 통계가 표시됩니다.")

    st.divider()
    st.write(f"**현재 회차:** {st.session_state.current_exam}")
    st.write(f"**진행률:** {st.session_state.idx + 1} / {len(exam_data)}")
    st.write(f"**맞힌 개수:** {st.session_state.score}개")
    st.write(f"**틀린 개수:** {incorrect_count}개")
    
    if st.button("학습 종료 및 결과 보기", use_container_width=True):
        st.session_state.idx = len(exam_data)
        st.rerun()
