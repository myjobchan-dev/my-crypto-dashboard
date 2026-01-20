import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime, timedelta
import time
import random

# ========================================
# PAGE CONFIG
# ========================================
st.set_page_config(
    page_title="กระดานวิเคราะห์ราคา",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# CUSTOM CSS - NEON THEME
# ========================================
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    h1, h2, h3 {
        color: #00ffff;
        text-shadow: 0 0 10px #00ffff, 0 0 20px #00ffff;
    }
    .metric-card {
        background: rgba(0, 255, 255, 0.1);
        border: 2px solid #00ffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
    }
    div[data-testid="stMetricValue"] {
        color: #00ffff;
        font-size: 2rem;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 1.2rem;
    }
    .news-link {
        color: #00ffff;
        text-decoration: none;
        padding: 10px;
        display: block;
        border-left: 3px solid #00ffff;
        margin: 10px 0;
        background: rgba(0, 255, 255, 0.05);
        transition: all 0.3s;
    }
    .news-link:hover {
        background: rgba(0, 255, 255, 0.2);
        padding-left: 20px;
    }
    .fear-greed-box {
        background: rgba(255, 165, 0, 0.1);
        border: 2px solid #FFA500;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 0 30px rgba(255, 165, 0, 0.4);
    }
    .fear-greed-value {
        font-size: 4rem;
        font-weight: bold;
        color: #FFA500;
        text-shadow: 0 0 20px #FFA500;
    }
    .clock {
        color: #00ffff;
        font-size: 1.2rem;
        text-align: center;
        margin: 10px 0;
    }
    .ai-signal-box {
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(0, 0, 0, 0.3);
    }
    .signal-green {
        background: rgba(0, 255, 0, 0.2);
        border: 2px solid #00ff00;
        color: #00ff00;
    }
    .signal-blue {
        background: rgba(0, 150, 255, 0.2);
        border: 2px solid #0096ff;
        color: #0096ff;
    }
    .signal-red {
        background: rgba(255, 0, 0, 0.2);
        border: 2px solid #ff0000;
        color: #ff0000;
    }
    .signal-gray {
        background: rgba(128, 128, 128, 0.2);
        border: 2px solid #808080;
        color: #cccccc;
    }
</style>
""", unsafe_allow_html=True)

# ========================================
# DATA UPDATE FUNCTION (WITH AUTO-RESET)
# ========================================
def update_data():
    """ดึงข้อมูลราคาล่าสุดและบันทึกลง CSV พร้อมตรวจสอบอายุข้อมูล"""
    csv_file = 'crypto_prices.csv'

    # ⚠️ AUTO-RESET - ตรวจสอบอายุข้อมูล
    should_reset = False
    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0 and 'timestamp' in df.columns:
                # ตรวจสอบ timestamp ล่าสุด
                last_timestamp = pd.to_datetime(df['timestamp'].iloc[-1])
                current_time = pd.Timestamp.now() + pd.Timedelta(hours=7)
                time_difference = current_time - last_timestamp

                # ถ้าข้อมูลเก่ากว่า 1 ชั่วโมง -> ลบไฟล์และเริ่มใหม่
                if time_difference > timedelta(hours=1):
                    os.remove(csv_file)
                    should_reset = True
                    st.sidebar.info(f"♻️ รีเซ็ตข้อมูล: ข้อมูลเก่า {time_difference.seconds // 3600} ชั่วโมง")
            else:
                # ไฟล์ว่าง -> ลบและเริ่มใหม่
                should_reset = True
        except Exception:
            should_reset = True

    # ตรวจสอบว่าไฟล์มีอยู่และมี columns ถูกต้องหรือไม่
    need_recreate = False
    if not os.path.exists(csv_file):
        need_recreate = True
    else:
        try:
            df = pd.read_csv(
