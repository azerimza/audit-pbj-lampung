import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="REKONSILIASI DATA", layout="wide")

st.markdown("""
    <style>
    .stat-card {
        background-color: #ffffff; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid #0c2461;
        text-align: center; margin-bottom: 20px;
