from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser



llm = ChatGroq(model="openai/gpt-oss-20b")

HUMAN_STYLE = """Write like a person, not like an AI:
- Vary your sentence length. Some short. Others longer, with a clause that earns its place.
- Use contractions (it's, don't, you'll) and talk straight to the reader as "you".
- Replace vague claims with a concrete example, a number, or a small story.
- Having an opinion is fine. Saying "I" is fine.
- Never use these words and phrases: "in today's fast-paced world", "delve", "moreover",
  "furthermore", "unlock", "leverage", "robust", "seamless", "game-changer",
  "it's worth noting", "navigate the landscape", "at the end of the day".
- Do not start every section the same way.
- Only use a bullet list when the content really is a list. Prefer paragraphs.
- Do not end with a summary of what you just said. End with one useful thought."""

OUTLINE_PROMPT = ChatPromptTemplate.from_template(
    "Write a short outline for a blog post.\n\n"
    "Topic: {topic}\n"
    "Tone: {tone}\n\n"
    "Give me:\n"
    "- one opening line that makes the reader curious\n"
    "- 4 section headings\n"
    "- 5 key points the post must cover\n\n"
    "Just the outline. Do not write the post."
)

DRAFT_PROMPT = ChatPromptTemplate.from_template(
    "Write a blog post from this outline.\n\n"
    "{outline}\n\n"
    + HUMAN_STYLE
    + "\n\n"
    "Tone: {tone}\n"
    "Output markdown, with the section headings as ###.\n"
    "Make it as long or as short as the topic actually needs."
)

POLISH_PROMPT = ChatPromptTemplate.from_template(
    "Improve this blog post without changing what it says.\n\n"
    + HUMAN_STYLE
    + "\n\n"
    "Also:\n"
    "- add a good # title at the top\n"
    "- keep the markdown\n\n"
    "Reply with the improved post only, no commentary.\n\n"
    "{draft}"
)

outline_chain=OUTLINE_PROMPT | llm | StrOutputParser()
draft_chain=DRAFT_PROMPT | llm | StrOutputParser()
polish_chain=POLISH_PROMPT | llm | StrOutputParser()

### UI DESIGN
st.subheader("Blog Post Generator")
st.caption("Outline -> Draft -> Polish. Three prompts , three chains.")

topic=st.text_input("Blog Title", "Why is genai becoming so popular?")
tone=st.selectbox("Tone", ["direct","formal", "Casual", "Inspirational"])

if st.button("Generate",type="primary"):
    with st.spinner("Generating outline..."):
        outline=outline_chain.invoke({"topic":topic,"tone":tone})
    
    with st.spinner("Generating draft..."):
        draft=draft_chain.invoke({"outline":outline,"tone":tone})
        
    with st.spinner("Polishing draft..."):
        polished=polish_chain.invoke({"draft":draft})   
        
    st.markdown(polished)  
    
    with st.expander("Raw Blog",expanded=False):
        st.code(polished)      
  
    