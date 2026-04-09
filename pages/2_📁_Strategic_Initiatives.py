"""CR Pulse — Strategic Initiatives (all initiatives view)"""
import streamlit as st
from utils.initiatives_renderer import render_initiatives

target = st.session_state.pop('initiatives_target', None)
render_initiatives(target)
