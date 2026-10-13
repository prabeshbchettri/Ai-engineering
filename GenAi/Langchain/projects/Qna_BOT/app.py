from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
import streamlit as st

llm = ChatGroq(model="openai/gpt-oss-20b")
if "messages" not in st.session_state:
  st.session_state.messages=[]


# UI
st.subheader("Qna Chatbot")
for msg in st.session_state.messages:
  st.chat_message(msg.get("role")).markdown(msg.get("content"))
query=st.chat_input("Ask anything.")
if query:
  
  st.session_state.messages.append({"role":"user","content":query})
  st.chat_message("User").markdown(query)
  res=llm.invoke(st.session_state.messages)
  st.session_state.messages.append({"role":"ai","content":res.content})
  st.chat_message("ai").markdown(res.content)

# while True:
#   query=input("User: ")
#   if query == "exit":
#     break
#   history.append({"role":"user","content":query})
#   res=llm.invoke(history)
#   print("AI: ",res.content)
#   history.append({"role":"ai","content":res.content})