"""Streamlit UI for the Cinema ticket-booking agent (folder 02_booking_agent).

This app is a thin chat interface on top of the EXISTING LangGraph agent defined
in ``agent.py`` (``final_graph``). It does NOT re-implement the workflow, the
intent classifier, the database logic, or the prompts.

How it talks to the agent (see ``test.ipynb`` for the same calls):
- Start / continue a turn:  ``final_graph.invoke({"user_message": ...}, config)``
- Answer a confirmation:   ``final_graph.invoke(Command(resume="yes"/"no"), config)``

The only place the graph pauses is ``confirm_booking_node`` (an ``interrupt``).
When that happens the agent's prompt is shown in the chat and the next message
you type is sent back as the resume value. Confirming a booking performs the
agent's normal, real behaviour (it writes to ``cinema.db``), explained in the UI.
"""

import os
import uuid

import streamlit as st
import streamlit.components.v1 as components

# ``Command`` is the LangGraph API used to resume an interrupted graph.
from langgraph.types import Command


# --------------------------------------------------------------------------- #
# Agent loading (cached so the graph is built once per Streamlit process)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def load_agent():
    """Return ``(graph, error)``.

    Imports the existing compiled graph from ``agent.py``. Loading is wrapped so
    a missing dependency or a configuration error shows a friendly message
    instead of crashing the page.
    """
    try:
        from agent import final_graph

        return final_graph, None
    except Exception as exc:  # pragma: no cover - surfaced to the user
        return None, exc


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def get_field(result, name, default=""):
    """Read a field from the graph result whether it is a dict or a model."""
    try:
        if isinstance(result, dict):
            return result.get(name, default)
        return getattr(result, name, default)
    except Exception:
        return default


def get_pending_interrupt(graph, config):
    """Return the interrupt prompt if the graph is paused, else ``None``.

    The agent pauses only at ``confirm_booking_node``. We inspect the checked
    state instead of guessing, so the UI knows it must ask for a confirmation.
    """
    try:
        snapshot = graph.get_state(config)
    except Exception:
        return None

    if not snapshot or not snapshot.next:
        return None

    for task in snapshot.tasks or []:
        for intr in getattr(task, "interrupts", None) or []:
            value = getattr(intr, "value", intr)
            if isinstance(value, dict):
                return value.get("message") or str(value)
            return str(value)

    return "The assistant is waiting for your confirmation. Reply Yes or No."


def copy_button(text, key, label="Copy message"):
    """Render a self-contained clipboard button.

    Uses the async Clipboard API and falls back to ``execCommand``. Success is
    reported by the component only after the browser confirms the write, so we
    never claim a copy happened without proof. Rendered inside an isolated
    ``components.html`` iframe.
    """
    import json

    safe_text = json.dumps(text).replace("</", "<\\/")
    template = """
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
  <button id="__BTN__" style="background:#7c3aed;color:#fff;border:none;
      border-radius:6px;padding:7px 16px;font-size:13px;font-weight:600;
      cursor:pointer;">__LABEL__</button>
  <span id="__MSG__" style="margin-left:10px;font-size:13px;font-weight:600;"></span>
</div>
<script>
  (function () {
    var text = __TEXT__;
    var btn = document.getElementById("__BTN__");
    var msg = document.getElementById("__MSG__");
    function show(t, color) {
      msg.style.color = color; msg.textContent = t;
      setTimeout(function () { msg.textContent = ""; }, 3000);
    }
    function fallback() {
      try {
        var ta = document.createElement("textarea");
        ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.focus(); ta.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        show(ok ? "\u2705 Copied!" : "\u26a0\ufe0f Copy blocked \u2014 select and press Ctrl+C.",
             ok ? "#1e8e3e" : "#c62828");
      } catch (e) {
        show("\u26a0\ufe0f Copy blocked \u2014 select and press Ctrl+C.", "#c62828");
      }
    }
    btn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
          .then(function () { show("\u2705 Copied!", "#1e8e3e"); })
          .catch(function () { fallback(); });
      } else { fallback(); }
    });
  })();
</script>
"""
    token = "c" + uuid.uuid4().hex
    html = (
        template.replace("__BTN__", "btn_" + token)
        .replace("__MSG__", "msg_" + token)
        .replace("__LABEL__", label)
        .replace("__TEXT__", safe_text)
    )
    components.html(html, height=44)


# --------------------------------------------------------------------------- #
# Page setup
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="CinemaBot", page_icon="🎬", layout="centered")

st.title("🎬 CinemaBot")
st.caption(
    "Chat with the movie ticket-booking assistant. Ask about movies, book seats, "
    "check or cancel a booking."
)

graph, load_error = load_agent()
if graph is None:
    st.error("The booking agent could not be loaded.")
    st.exception(load_error)
    st.stop()

if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "No GROQ_API_KEY found. Add it to the shared .env file "
        "(Agentic_ai/Langraph/.env) before chatting."
    )

# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "awaiting" not in st.session_state:
    st.session_state.awaiting = False

config = {"configurable": {"thread_id": st.session_state.thread_id}}


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("CinemaBot")
    st.write(
        "This interface calls the existing LangGraph agent in `agent.py` "
        "(`final_graph`). The agent logic is untouched."
    )
    st.markdown(
        "**Try things like:**\n"
        "- *What movies are showing?*\n"
        "- *How much is a ticket for Inception?*\n"
        "- *Book 2 tickets for Avengers for Alice*\n"
        "- *Is booking 1 confirmed?*\n"
        "- *Cancel booking 1*"
    )
    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.awaiting = False
        st.rerun()

    st.divider()
    st.caption(
        "ℹ️ Confirming a booking performs the agent's real action — it is saved "
        "to the local `cinema.db`. There is no email sending here."
    )


# --------------------------------------------------------------------------- #
# Render chat history
# --------------------------------------------------------------------------- #
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        is_last = i == len(st.session_state.messages) - 1
        if is_last and message["role"] == "assistant":
            copy_button(message["content"], key=f"copy_{i}")


# --------------------------------------------------------------------------- #
# Handle new input
# --------------------------------------------------------------------------- #
placeholder = (
    "Type Yes or No to confirm the booking…"
    if st.session_state.awaiting
    else "Ask about movies, or book/cancel a ticket…"
)

if prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        with st.spinner("CinemaBot is thinking…"):
            if st.session_state.awaiting:
                # Resume the paused confirmation node with the user's reply.
                result = graph.invoke(Command(resume=prompt), config)
                st.session_state.awaiting = False
            else:
                # Normal turn: classify intent and run the matching branch.
                result = graph.invoke({"user_message": prompt}, config)

        interrupt_prompt = get_pending_interrupt(graph, config)

        if interrupt_prompt:
            # The graph is paused at ``confirm_booking_node`` (before the
            # response node), so any ``result`` still in the checkpoint is from
            # a PREVIOUS turn. Show only the agent's confirmation prompt here.
            st.session_state.messages.append(
                {"role": "assistant", "content": interrupt_prompt}
            )
            st.session_state.awaiting = True
        else:
            reply = str(get_field(result, "result", "") or "").strip()
            if reply:
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )
            else:
                error = get_field(result, "data", {})
                error = error.get("error") if isinstance(error, dict) else None
                fallback = error or (
                    "I couldn't produce a response for that. "
                    "Try rephrasing your request."
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": fallback}
                )

    except Exception as exc:
        st.session_state.awaiting = False
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"⚠️ Something went wrong while talking to the agent: `{exc}`",
            }
        )

    st.rerun()
