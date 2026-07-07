"""
Application Tracker Copilot — Streamlit frontend.

Run with: streamlit run app.py
(Make sure the FastAPI backend is already running on localhost:8000)
"""
import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Application Tracker Copilot", layout="wide")
st.title("📋 Application Tracker Copilot")

tab_pipeline, tab_add, tab_generate = st.tabs(["Pipeline", "Add Application", "Generate Answer"])

# ---------------------------------------------------------------------------
# Pipeline view
# ---------------------------------------------------------------------------
with tab_pipeline:
    status_filter = st.selectbox(
        "Filter by status",
        ["all", "applied", "oa_takehome", "interview", "offer", "rejected", "withdrawn"],
    )
    params = {} if status_filter == "all" else {"status": status_filter}
    try:
        resp = requests.get(f"{API_URL}/applications", params=params, timeout=10)
        resp.raise_for_status()
        apps = resp.json()
    except requests.RequestException as e:
        st.error(f"Couldn't reach the backend: {e}")
        apps = []

    if apps:
        df = pd.DataFrame(apps)
        display_cols = [c for c in ["company", "role", "status", "deadline", "created_at"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)

        st.subheader("Update an application")
        id_to_company = {a["_id"]: f"{a['company']} — {a['role']}" for a in apps}
        selected_id = st.selectbox(
            "Select application", options=list(id_to_company.keys()),
            format_func=lambda x: id_to_company[x],
        )
        new_status = st.selectbox(
            "New status",
            ["applied", "oa_takehome", "interview", "offer", "rejected", "withdrawn"],
        )
        if st.button("Update status"):
            r = requests.patch(f"{API_URL}/applications/{selected_id}", json={"status": new_status})
            if r.ok:
                st.success("Updated.")
                st.rerun()
            else:
                st.error(r.text)
    else:
        st.info("No applications yet — add one in the next tab.")

# ---------------------------------------------------------------------------
# Add application (with auto-parse)
# ---------------------------------------------------------------------------
with tab_add:
    st.subheader("Paste a job description")
    jd_text = st.text_area("Job description text", height=200)

    if "parsed" not in st.session_state:
        st.session_state.parsed = None

    if st.button("Auto-parse JD"):
        if jd_text.strip():
            r = requests.post(f"{API_URL}/parse-jd", json={"jd_text": jd_text})
            if r.ok:
                st.session_state.parsed = r.json()
            else:
                st.error(r.text)
        else:
            st.warning("Paste a job description first.")

    parsed = st.session_state.parsed or {}
    company = st.text_input("Company", value=parsed.get("company") or "")
    role = st.text_input("Role", value=parsed.get("role") or "")
    deadline = st.text_input("Deadline (as written)", value=parsed.get("deadline") or "")
    key_reqs = st.text_area(
        "Key requirements (one per line)",
        value="\n".join(parsed.get("key_requirements", [])) if parsed else "",
    )

    if st.button("Save application"):
        payload = {
            "company": company,
            "role": role,
            "jd_text": jd_text,
            "notes": "",
            "key_requirements": [r for r in key_reqs.split("\n") if r.strip()],
        }
        r = requests.post(f"{API_URL}/applications", json=payload)
        if r.ok:
            st.success(f"Saved {company} — {role}")
            st.session_state.parsed = None
        else:
            st.error(r.text)

# ---------------------------------------------------------------------------
# Generate a drafted answer
# ---------------------------------------------------------------------------
with tab_generate:
    st.subheader("Draft a first-pass answer")
    st.caption("Grounded in your resume — review and edit before submitting anywhere.")

    try:
        apps = requests.get(f"{API_URL}/applications", timeout=10).json()
    except requests.RequestException:
        apps = []

    app_options = {None: "— no specific application —"}
    app_options.update({a["_id"]: f"{a['company']} — {a['role']}" for a in apps})
    selected_app = st.selectbox(
        "Tie to an application (optional, adds JD context)",
        options=list(app_options.keys()),
        format_func=lambda x: app_options[x],
    )

    question = st.text_area("Question / prompt to answer", height=120)

    if st.button("Generate draft"):
        if question.strip():
            payload = {"question": question, "application_id": selected_app}
            r = requests.post(f"{API_URL}/generate-answer", json=payload)
            if r.ok:
                data = r.json()
                st.text_area("Draft answer", value=data["answer"], height=300)
                with st.expander("Resume chunks used"):
                    for chunk in data["sources_used"]:
                        st.text(chunk[:300] + "...")
            else:
                st.error(r.text)
        else:
            st.warning("Enter a question first.")
