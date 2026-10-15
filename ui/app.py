import os

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Помощник по коду 1С", layout="wide")
st.title("Помощник по коду 1С")

tab_chat, tab_docs = st.tabs(["Вопросы", "Документация"])

with tab_chat:
    question = st.text_input("Вопрос по конфигурации")
    if st.button("Спросить") and question:
        with st.spinner("Ищу ответ"):
            r = requests.post(f"{API}/ask", json={"question": question}, timeout=900)
            r.raise_for_status()
            st.session_state["result"] = {**r.json(), "question": question}

    res = st.session_state.get("result")
    if res:
        st.markdown(res["answer"])
        with st.expander("Источники"):
            for s in res["sources"]:
                st.write(f"{s['name']} ({s['module']})")
        comment = st.text_area("Комментарий главного разработчика")
        col1, col2 = st.columns(2)
        payload = {
            "question": res["question"],
            "answer": res["answer"],
            "procedure_ids": [s["id"] for s in res["sources"]],
            "comment": comment,
        }
        if col1.button("Верно"):
            requests.post(f"{API}/feedback", json={**payload, "verdict": "ok"})
            st.success("Оценка сохранена")
        if col2.button("Неверно"):
            requests.post(f"{API}/feedback", json={**payload, "verdict": "wrong"})
            st.warning("Оценка сохранена, документация перегенерируется")

with tab_docs:
    query = st.text_input("Имя процедуры")
    if query:
        items = requests.get(f"{API}/procedures", params={"q": query}).json()
        labels = {f"{i['name']} ({i['path']})": i["id"] for i in items}
        if labels:
            choice = st.selectbox("Результаты", list(labels))
            doc = requests.get(f"{API}/documentation/{labels[choice]}").json()
            if doc["content_md"]:
                st.caption(f"Версия {doc['version']}")
                st.markdown(doc["content_md"])
            else:
                st.info("Документации пока нет")
        else:
            st.info("Ничего не найдено")
