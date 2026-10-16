"""Streamlit UI for the Email Agent in this folder (01_email_Agent).

This app is a thin interface on top of the EXISTING LangGraph agent defined in
``agent.py``. It only generates email DRAFTS and never sends email.

Design rules followed:
- The agent is the single source of truth: we import its ``final_graph`` and
  call it. The workflow is not re-implemented here.
- We call the graph with a ``question`` string and read back ``subject`` /
  ``body``. The graph pauses at the human-review ``interrupt`` before the
  ``send`` node, so drafting never triggers an email.
- We NEVER resume the graph with "yes", so ``send_mail`` is never called.
"""

import json
import os
import uuid

import streamlit as st

# ``Command`` is the LangGraph API used to resume an interrupted graph (the
# agent's human-review step) with feedback.
from langgraph.types import Command


@st.cache_resource(show_spinner=False)
def load_agent():
    """Return (graph, error).

    Imports the existing agent's compiled graph once per Streamlit process.
    Loading is wrapped so a missing dependency or missing API key shows a
    friendly message instead of a crash. ``agent.py`` no longer runs its CLI
    loop on import (it is guarded by ``if __name__ == "__main__":``), so
    importing ``final_graph`` is safe.
    """
    try:
        from agent import final_graph

        return final_graph, None
    except Exception as exc:  # pragma: no cover - surfaced to the user
        return None, exc


def build_query(purpose, recipient_name, recipient_email, details, signature):
    """Combine the form fields into the single free-text question the agent expects."""
    parts = [f"I want to send an email. Purpose: {purpose.strip()}."]
    if recipient_name.strip():
        parts.append(f"The recipient's name is {recipient_name.strip()}.")
    if recipient_email.strip():
        parts.append(f"The recipient's email address is {recipient_email.strip()}.")
    if details.strip():
        parts.append(f"Key points to include: {details.strip()}.")
    if signature.strip():
        parts.append(f"Please sign the email as {signature.strip()}.")
    return " ".join(parts)


def copy_button(text, label="Copy Email", height=58):
    """Render a small, self-contained clipboard button.

    Uses the async Clipboard API and confirms success only when the browser
    resolves the write (with an execCommand fallback). The confirmation text is
    shown by the component itself, so we never claim success without proof.
    """
    safe_text = json.dumps(text).replace("</", "<\\/")
    template = """
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;">
  <button id="__BTN__" style="background:#ff4b4b;color:#fff;border:none;
      border-radius:6px;padding:9px 20px;font-size:15px;font-weight:600;
      cursor:pointer;">__LABEL__</button>
  <span id="__MSG__" style="margin-left:12px;font-size:14px;font-weight:600;"></span>
</div>
<script>
  (function () {
    var text = __TEXT__;
    var btn = document.getElementById("__BTN__");
    var msg = document.getElementById("__MSG__");
    function show(t, color) { msg.style.color = color; msg.textContent = t;
      setTimeout(function () { msg.textContent = ""; }, 3000); }
    btn.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
          show("✅ Copied to clipboard!", "#1e8e3e");
        }).catch(function () { fallback(); });
      } else { fallback(); }
    });
    function fallback() {
      try {
        var ta = document.createElement("textarea");
        ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.focus(); ta.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (ok) { show("✅ Copied to clipboard!", "#1e8e3e"); }
        else { show("⚠️ Copy blocked — select the text and press Ctrl+C.", "#c62828"); }
      } catch (e) {
        show("⚠️ Copy blocked — select the text and press Ctrl+C.", "#c62828");
      }
    }
  })();
</script>
"""
    token = uuid.uuid4().hex
    html = (
        template.replace("__BTN__", "btn_" + token)
        .replace("__MSG__", "msg_" + token)
        .replace("__LABEL__", label)
        .replace("__TEXT__", safe_text)
    )
    st.iframe(html, height=height, width="stretch", alt="Copy email button")


def get_field(result, name, default=""):
    """Read a field from the graph result whether it is a dict or a model."""
    try:
        if hasattr(result, "get"):
            return result.get(name, default) or default
        return getattr(result, name, default) or default
    except Exception:
        return default


def set_email_fields(subject, body):
    """Defer updates to the editable email widgets to the next rerun.

    Buttons that appear *below* the email widgets cannot assign to their
    ``session_state`` keys in the same run (Streamlit forbids changing a widget
    value after it has been created). So we stash the new values and apply them
    at the top of the script, before the widgets are created.
    """
    st.session_state["__pending_subject"] = subject
    st.session_state["__pending_body"] = body


# --------------------------------------------------------------------------- #
# Page setup
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="AI Email Assistant", page_icon="✉️", layout="centered")

st.title("✉️ AI Email Assistant")
st.caption(
    "Generate a professional email draft with AI. Drafts only — this app never "
    "sends email."
)

# Session state defaults. ``subject_input`` / ``body_input`` drive the editable
# widgets and are updated programmatically after each generation.
for key, value in {
    "subject_input": "",
    "body_input": "",
    "thread_id": "",
    "generated": False,
    "info": "",
}.items():
    st.session_state.setdefault(key, value)

# Apply any deferred email-widget updates requested by buttons that sit below
# the widgets (regenerate / start over).
if "__pending_subject" in st.session_state:
    st.session_state["subject_input"] = st.session_state.pop("__pending_subject")
    st.session_state["body_input"] = st.session_state.pop("__pending_body")

graph, load_error = load_agent()
if graph is None:
    st.error("The email agent could not be loaded.")
    st.exception(load_error)
    st.stop()

if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "No GROQ_API_KEY found. Add it to the project's .env file "
        "(Agentic_ai/Langraph/.env) before generating an email."
    )

# --------------------------------------------------------------------------- #
# Input form
# --------------------------------------------------------------------------- #
with st.form("email_form"):
    st.subheader("Email details")
    purpose = st.text_area(
        "Purpose / topic of the email *",
        placeholder="e.g. Request an internship opportunity for summer 2026",
        height=90,
    )
    col1, col2 = st.columns(2)
    with col1:
        recipient_name = st.text_input(
            "Recipient's name (optional)", placeholder="e.g. Atul Malhotra"
        )
    with col2:
        recipient_email = st.text_input(
            "Recipient's email (optional)", placeholder="e.g. atul@example.com"
        )
    details = st.text_area(
        "Key points / extra context (optional)",
        placeholder="e.g. available from June, attach resume, mention 3 months",
        height=80,
    )
    signature = st.text_input(
        "Sign the email as (optional)", placeholder="e.g. Prateek Mishra"
    )

    generate = st.form_submit_button("Generate Email", type="primary", use_container_width=True)

# --------------------------------------------------------------------------- #
# Generate
# --------------------------------------------------------------------------- #
if generate:
    if not purpose.strip():
        st.warning("Please enter the purpose of the email.")
    else:
        query = build_query(purpose, recipient_name, recipient_email, details, signature)
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        with st.spinner("Drafting your email..."):
            try:
                result = graph.invoke({"question": query}, config=config)
                st.session_state.thread_id = thread_id
                st.session_state.subject_input = get_field(result, "subject")
                st.session_state.body_input = get_field(result, "body")
                st.session_state.generated = True
                st.session_state.info = ""
            except Exception as exc:
                st.session_state.generated = False
                st.error(f"Could not generate the email: {exc}")

# --------------------------------------------------------------------------- #
# Generated email (editable + copy-friendly)
# --------------------------------------------------------------------------- #
if st.session_state.generated:
    st.divider()
    st.subheader("Generated email")
    st.caption("Edit the subject or body below, then copy the final email.")

    subject = st.text_input("Subject", key="subject_input")
    body = st.text_area("Body", key="body_input", height=420)

    full_email = f"Subject: {subject}\n\n{body}"
    copy_button(full_email)

    with st.expander("Show full email as plain text (fallback copy)"):
        st.code(full_email, language=None)

    # Regenerate using the agent's own feedback loop (still draft-only).
    st.divider()
    st.subheader("Not happy with it?")
    feedback = st.text_area(
        "Describe the changes you want (optional)",
        placeholder="e.g. Make it shorter and more formal. Remove the placeholder name.",
        height=80,
    )
    col_r1, col_r2 = st.columns([1, 1])
    with col_r1:
        regenerate = st.button("Regenerate with feedback", use_container_width=True)
    with col_r2:
        start_over = st.button("Start over", use_container_width=True)

    if regenerate:
        if not feedback.strip():
            st.warning("Please describe the changes you want first.")
        else:
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            with st.spinner("Revising your email..."):
                try:
                    result = graph.invoke(Command(resume=feedback), config=config)
                    new_subject = get_field(result, "subject")
                    new_body = get_field(result, "body")
                    if new_subject or new_body:
                        set_email_fields(new_subject, new_body)
                        st.session_state.info = "Updated using your feedback."
                    else:
                        st.session_state.info = get_field(result, "response")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not regenerate the email: {exc}")

    if start_over:
        set_email_fields("", "")
        st.session_state.thread_id = ""
        st.session_state.generated = False
        st.session_state.info = ""
        st.rerun()

if st.session_state.info:
    st.info(st.session_state.info)
