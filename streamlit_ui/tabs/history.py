"""History tab rendering."""

import streamlit as st

from utils.history import get_history, list_history


def render_history_tab():
    st.header("Saved History")
    limit = st.number_input(
        "Items to show", min_value=5, max_value=100, value=25, step=5
    )
    items = list_history(int(limit))
    if not items:
        st.caption("No saved history yet.")
        return
    labels = [
        f"{item['id']} | {item['event_type']} | {item['title']} | {item['created_at']}"
        for item in items
    ]
    selected = st.selectbox("History item", labels)
    selected_id = int(selected.split(" | ", 1)[0])
    item = get_history(selected_id)
    if item:
        st.json(item)
