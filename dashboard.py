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
            df = pd.read_csv(csv_file)
            # ตรวจสอบว่ามี columns ที่ถูกต้องหรือไม่
            required_cols = ['timestamp', 'BTC_price', 'ETH_price', 'Gold_price']
            if not all(col in df.columns for col in required_cols):
                need_recreate = True
        except:
            need_recreate = True

    # สร้างไฟล์ใหม่ถ้าจำเป็น
    if need_recreate or should_reset:
        df = pd.DataFrame(columns=['timestamp', 'BTC_price', 'ETH_price', 'Gold_price'])
        df.to_csv(csv_file, index=False)

    # อ่านข้อมูลเดิม
    df = pd.read_csv(csv_file)

    # ========================================================
    # ✨ FIX 1: ปรับราคาเริ่มต้นให้ใกล้เคียงความจริง (แก้กราฟแบน)
    # ========================================================
    last_btc = 90000.0 if len(df) == 0 else float(df['BTC_price'].iloc[-1]) if not df.empty else 90000.0
    last_eth = 3000.0 if len(df) == 0 else float(df['ETH_price'].iloc[-1]) if not df.empty else 3000.0
    last_gold = 2600.0 if len(df) == 0 else float(df['Gold_price'].iloc[-1]) if not df.empty else 2600.0

    try:
        # ดึงราคา BTC & ETH จาก CoinGecko API (ฟรี, ไม่ต้อง API key)
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd',
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            btc_price = data.get('bitcoin', {}).get('usd', last_btc)
            eth_price = data.get('ethereum', {}).get('usd', last_eth)
        else:
            # ใช้ราคาล่าสุด + สุ่มเล็กน้อย
            btc_price = last_btc * (1 + random.uniform(-0.005, 0.005))
            eth_price = last_eth * (1 + random.uniform(-0.005, 0.005))
    except:
        # ถ้า API ล้มเหลว ใช้ราคาล่าสุด + สุ่มเล็กน้อย (DON'T CRASH!)
        btc_price = last_btc * (1 + random.uniform(-0.005, 0.005))
        eth_price = last_eth * (1 + random.uniform(-0.005, 0.005))

    # จำลองราคาทองคำ (2600 +/- ความผันผวนเล็กน้อย)
    gold_price = last_gold + random.uniform(-5, 5)

    # เพิ่มข้อมูลใหม่ (เวลาไทย +7)
    new_row = pd.DataFrame([{
        'timestamp': (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        'BTC_price': round(btc_price, 2),
        'ETH_price': round(eth_price, 2),
        'Gold_price': round(gold_price, 2)
    }])

    df = pd.concat([df, new_row], ignore_index=True)

    # กรองข้อมูลที่มีค่าน้อยกว่า 100 (ป้องกันกราฟกระโดด)
    df = df[df['BTC_price'] > 100]

    # เก็บแค่ 1000 แถวล่าสุด (ประหยัดพื้นที่)
    if len(df) > 1000:
        df = df.tail(1000)

    df.to_csv(csv_file, index=False)

    return df

# ========================================
# TIER 1 AI: SIGNAL GENERATOR FOR MAIN CHARTS
# ========================================
def get_signal(price, ma, rsi):
    """
    🤖 TIER 1 AI: สร้างสัญญาณการลงทุนจาก Price, MA, และ RSI
    Returns: (signal_text, signal_class)
    """
    # Logic 1: Price > MA & RSI < 45 -> Strong Buy (Green)
    if price > ma and rsi < 45:
        return "🚀 โอกาสสะสม (Strong Buy)", "signal-green"

    # Logic 2: Price > MA -> Hold/Uptrend (Blue)
    elif price > ma:
        return "🟢 ถือรันเทรนด์ (Hold/Uptrend)", "signal-blue"

    # Logic 3: Price < MA & RSI > 55 -> Sell Signal (Red)
    elif price < ma and rsi > 55:
        return "🔴 ระวังแรงขาย (Sell Signal)", "signal-red"

    # Logic 4: Else -> Wait (Gray)
    else:
        return "⚪ ชะลอการลงทุน (Wait)", "signal-gray"

# ========================================
# F
