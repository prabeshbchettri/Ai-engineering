from dotenv import load_dotenv
load_dotenv()


#### Import all the packages
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field
from typing import Annotated, Literal
from send_email import send_mail


#### Deine the LLM Object
llm = ChatGroq(model="openai/gpt-oss-20b")

### Global State

class EmailState(BaseModel):
    question: str = ""
    mail_reason: str = ""
    recipient_name: str = ""
    recipient_email: str = ""
    subject: str = ""
    body: str = ""
    feedback: str = ""
    feedback_count: int = 0 ## Max Count 3
    response: str = ""
    

    
#### Retriever Node

class UserDetails(BaseModel):
    mail_reason: str = Field(description="Reason of the email, like why user want to send this email")
    recipient_name: str = Field(description="recipient / reciever name, if available, else '' ")
    recipient_email: str = Field(description="recipient / reciever email address")
    
    
def retriever_node(state:EmailState) -> EmailState:
    llm_for_user_details = llm.with_structured_output(UserDetails)
    userDetails:UserDetails = llm_for_user_details.invoke(f"Retrieve the user details from this query: {state.question}.")
    
    if not userDetails.mail_reason or not userDetails.recipient_email:
        pass
    
    state.recipient_name = userDetails.recipient_name
    state.recipient_email = userDetails.recipient_email
    state.mail_reason = userDetails.mail_reason
    
    return state


#### Draft Node

class DraftEmail(BaseModel):
    subject: str = Field(description="Email subject within 40 Words")
    body: str = Field(description="Email Body including proper details, reason and greetings and others")


def draft_node(state:EmailState) -> EmailState:
    "Draft a Email"
    draft_email_llm = llm.with_structured_output(DraftEmail)
    
    prompt = f"""
        Write a email with these details:
        To: {state.recipient_name}
        Request: {state.mail_reason}
        
        Please write a proper mail body and subject. Without extra text. Mail body
        max size will be 200 Words.  
    """
    
    if state.feedback:
        prompt = f"""Revise this email based on the feedback below.
            Current Email: 
            Subject: {state.subject}
            Body: {state.body}

            Feedback: {state.feedback}

            Please write a proper mail body and subject. Without extra text and improvement based on the feedback. 
            Mail body max size will be 200 Words.  """
    
            
    draftEmail:DraftEmail = draft_email_llm.invoke(prompt)
    state.subject = draftEmail.subject
    state.body = draftEmail.body
    
    return state
    

### Review Node

def review_node(state:EmailState) -> EmailState:    
    response = interrupt({
        "message":"You want to approve this or re-write this email"
    })
    
    if response == "yes":
        state.feedback = ""
    else:
        state.feedback = response
        state.feedback_count = state.feedback_count + 1
    
    
    
    return state

    
def router(state:EmailState) -> Literal["draft", "send", "cancel"]:
    if not state.feedback or state.feedback.strip() == "":
        return "send"
    
    if state.feedback_count > 2:
        return "cancel"
    
    return "draft"
    
    

def cancel_node(state:EmailState) -> EmailState:
    state.response = "Email Not Sent, Because you have reached the limit of feedbacks"
    return state

    
def send_node(state:EmailState) -> EmailState:
    "Send final email"
    res = send_mail(state.recipient_email, state.subject, state.body)
    state.response = res
    return state
    
graph = StateGraph(EmailState)
graph.add_node("retriever", retriever_node)
graph.add_node("draft", draft_node)
graph.add_node("send", send_node)
graph.add_node("cancel", cancel_node)
graph.add_node("review_node", review_node)


graph.add_edge(START, "retriever")
graph.add_edge("retriever", "draft")
graph.add_edge("draft", "review_node")
graph.add_conditional_edges('review_node', router)
graph.add_edge("send", END)
graph.add_edge("cancel", END)

final_graph = graph.compile(checkpointer=InMemorySaver())


if __name__ == "__main__":
    while True:
        query = input("User: ")
        if query == "quit":
            print("Bye 👋")
            break
        
        config = {"configurable": {"thread_id":"2"}}
        res = final_graph.invoke(
            {"question":query},
            config=config
        )
    
        while True:
            state = final_graph.get_state(config)
            
            if not state.next:
                break
            
            print("\n", "-"*60)
            print("Subject: ", res["subject"])
            print("Body: ", res["body"])
            print("\n", "-"*60)
            
    
            feedback = input("Approve to send the mail or provide the feedback: ")
            res = final_graph.invoke(
                    Command(resume=feedback),
                    config=config
                )         
        
        print("AI: ", res["response"])
    
    
            
    
            
            
    
        
        