import os, uuid
from typing import Optional, Any, Dict
from pydantic import BaseModel
from fastapi import FastAPI
from langchain_core.tools import tool
from pydantic import BaseModel as PydanticModel

from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command

from langchain_openai import ChatOpenAI


OPENAI_API_KEY="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"


# -------- Tools --------
@tool
def search(query: str) -> str:
    """Demo search tool."""
    return f"Result for: {query}"

class AskHuman(PydanticModel):
    question: str

# -------- Model --------
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=OPENAI_API_KEY,
)
model = llm.bind_tools([search, AskHuman])

# -------- Nodes --------
def agent(state: MessagesState):
    resp = model.invoke(state["messages"])
    return {"messages": [resp]}

def route(state: MessagesState):
    msg = state["messages"][-1]
    if not getattr(msg, "tool_calls", None):
        return END
    name = msg.tool_calls[0]["name"]
    return "ask_human" if name == "AskHuman" else "tools"

def ask_human(state: MessagesState):
    tc = state["messages"][-1].tool_calls[0]
    q = AskHuman.model_validate(tc["args"]).question
    ans = interrupt({"question": q})  # pauses the graph
    return {"messages": [{
        "type": "tool",
        "tool_call_id": tc["id"],
        "content": ans
    }]}

# -------- Graph --------
builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode([search]))
builder.add_node("ask_human", ask_human)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route, path_map=["ask_human", "tools", END])
builder.add_edge("tools", "agent")
builder.add_edge("ask_human", "agent")

graph = builder.compile(checkpointer=InMemorySaver())

# -------- API --------
app = FastAPI(title="Simple HITL Chat")

class ChatBody(BaseModel):
    thread_id: Optional[str] = None
    message: Optional[str] = None   # send a new user message
    answer: Optional[Any] = None    # resume value for an interrupt

def run_stream(obj: Any, thread_id: str) -> Dict[str, Any]:
    """Run the graph with either inputs or Command(resume=...)."""
    config = {"configurable": {"thread_id": thread_id}}
    last_messages = []
    for event in graph.stream(obj, config, stream_mode="values"):
        if "messages" in event:
            last_messages = event["messages"]

    # Determine if we paused or finished
    state = graph.get_state(config)
    if state.interrupts:
        intr = state.interrupts[-1]
        return {
            "status": "interrupted",
            "thread_id": thread_id,
            "interrupt_id": intr.id,
            "question": intr.value,          # payload from interrupt(...)
            "partial": [m.content for m in last_messages],
        }
    return {
        "status": "completed",
        "thread_id": thread_id,
        "final": last_messages[-1].content if last_messages else None,
        "messages": [m.content for m in last_messages],
    }

@app.post("/chat")
def chat(body: ChatBody):
    thread_id = body.thread_id or str(uuid.uuid4())

    # 1) If client is answering a pending interrupt, resume first.
    if body.answer is not None:
        resume_result = run_stream(Command(resume=body.answer), thread_id)
        if resume_result["status"] == "interrupted":
            return resume_result
        # Optionally fall through to also process a new message in same call
        if body.message is None:
            return resume_result

    # 2) If a new user message is provided, run it.
    if body.message is not None:
        return run_stream({"messages": [("user", body.message)]}, thread_id)

    # 3) Nothing to do
    return {"status": "noop", "thread_id": thread_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)