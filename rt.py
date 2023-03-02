import streamlit as st
import openai

st.markdown('# ChatGPT demo')

openai.api_key = "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"


def init_session():
    if 'round' not in st.session_state:
        print("重置轮数")
        st.session_state['round'] = 1

    if 'question' not in st.session_state:
        print("重置问题记录")
        st.session_state['question'] = []

    if 'answer' not in st.session_state:
        print("重置回答记录")
        st.session_state['answer'] = []


init_session()
system_input = st.text_input('请设定 ChatGPT 角色（用于生成符合角色的回答）', "你是一个有用的AI助手")
latest_input = st.text_area('请输入内容')

if st.button('发送'):
    st.session_state['question'].append(latest_input)

    message_list = []
    dic_q_item = {"role": "system", "content": system_input}
    message_list.append(dic_q_item)
    for n in range(st.session_state['round']):
        # 第 n 轮，有 n 个问题，n - 1 个答案待组装
        if n - 1 >= 0:
            dic_a_item = {"role": "assistant", "content": st.session_state['answer'][n - 1]}
            message_list.append(dic_a_item)
        dic_q_item = {"role": "user", "content": st.session_state['question'][n]}
        message_list.append(dic_q_item)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=1000,
        user="wzy",
        messages=message_list,
    )

    answer = completion.choices[0].message['content']
    st.session_state['answer'].append(answer)

    col1, col2 = st.columns(2)

    for i in range(st.session_state['round']):
        with col1:
            st.text('User')
            st.write('  ' + st.session_state['question'][i])
            st.text(' ')
            st.write(' ')
        with col2:
            st.text(' ')
            st.write(' ')
            st.text('ChatGPT')
            st.write('  ' + st.session_state['answer'][i])

    st.session_state['round'] += 1

if st.button('清空对话记录'):
    st.session_state.clear()
