import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.graph_objects as go
import numpy as np
import requests

# RSI Calculation Function
def calculate_rsi(prices, period=7):
    """
    Calculate Relative Strength Index (RSI) for a given price series.
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    """
    if len(prices) < period:
        return None

    # Convert to pandas Series if not already
    prices = pd.Series(prices)

    # Calculate price changes
    delta = prices.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Calculate average gains and losses
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

# Fetch Crypto Fear & Greed Index
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_fear_greed_index():
    """
    Fetch the latest Crypto Fear & Greed Index from alternative.me API
    Returns a dict with value, classification, and timestamp
    """
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and len(data['data']) > 0:
            index_data = data['data'][0]
            value = int(index_data['value'])

            # Determine classification and emoji
            if value <= 25:
                classification = "😱 Extreme Fear"
                color = "#FF0000"  # Red
            elif value <= 50:
                classification = "😨 Fear"
                color = "#FFA500"  # Orange
            elif value <= 75:
                classification = "🙂 Greed"
                color = "#90EE90"  # Light Green
            else:
                classification = "🤑 Extreme Greed"
                color = "#006400"  # Dark Green

            return {
                'value': value,
                'classification': classification,
                'color': color,
                'timestamp': index_data.get('timestamp', '')
            }
        return None
    except Exception as e:
        st.error(f"Error fetching Fear & Greed Index: {e}")
        return None

# Fetch Top 10 Cryptocurrencies from CoinGecko
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_top_10_cryptos():
    """
    Fetch the top 10 cryptocurrencies by market cap from CoinGecko API
    Returns a DataFrame with Name, Current Price, 24h Change (%), Market Cap
    """
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 10,
            'page': 1,
            'sparkline': False
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Create DataFrame
        crypto_data = []
        for coin in data:
            crypto_data.append({
                'Name': coin['name'],
                'Symbol': coin['symbol'].upper(),
                'Current Price': coin['current_price'],
                '24h Change (%)': coin['price_change_percentage_24h'],
                'Market Cap': coin['market_cap']
            })

        df = pd.DataFrame(crypto_data)
        return df
    except Exception as e:
        st.error(f"Error fetching crypto data: {e}")
        return None

# Page configuration
st.set_page_config(
    page_title="Asset Price Dashboard",
    page_icon="📈",
    layout="wide"
)

# Title with Clock/Date
col_title, col_clock = st.columns([3, 1])

with col_title:
    st.title("📈 Asset Price Dashboard")
    st.markdown("Real-time tracking of Bitcoin (BTC), Ethereum (ETH), and Gold (GC=F) prices with trend analysis")

with col_clock:
    current_time = datetime.now()
    st.markdown(f"<h3 style='text-align: right; font-size: 1.2em; font-weight: bold;'>{current_time.strftime('%a %d %b %Y')}<br>{current_time.strftime('%H:%M:%S')}</h3>", unsafe_allow_html=True)

# Crypto Fear & Greed Index Display
st.markdown("---")
fear_greed_data = fetch_fear_greed_index()

if fear_greed_data:
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background-color: {fear_greed_data['color']}; border-radius: 10px; margin-bottom: 20px;'>
        <h2 style='color: white; margin: 0;'>Crypto Fear & Greed Index</h2>
        <h1 style='color: white; font-size: 3em; margin: 10px 0;'>{fear_greed_data['value']}</h1>
        <h2 style='color: white; margin: 0;'>{fear_greed_data['classification']}</h2>
    </div>
    """, unsafe_allow_html=True)

    # Educational Expander for Fear & Greed
    with st.expander('ℹ️ 🧠 วิธีอ่านค่า Fear & Greed (คลิกเพื่อเรียนรู้)'):
        st.markdown("""
**🌡️ มันคือ "ปรอทวัดอารมณ์ตลาด"**
ตลาดคริปโตขับเคลื่อนด้วยอารมณ์คนครับ

**0 - 24 (สีแดง): Extreme Fear (กลัวสุดขีด)** = คนเทขายหนีตาย ราคาร่วงยับเยิน (แต่มักเป็นจุดซื้อที่ดีที่สุด)

**25 - 49 (สีส้ม): Fear (กลัว)** = คนยังกังวล ไม่กล้าซื้อ (แบบที่เห็นในรูปตอนนี้คือ 44)

**50 - 74 (สีเหลือง/เขียวอ่อน): Greed (โลภ)** = ตลาดคึกคัก คนเริ่มไล่ซื้อ

**75 - 100 (สีเขียวเข้ม): Extreme Greed (โลภสุดขีด)** = คนแย่งกันซื้อแบบไม่ลืมหูลืมตา (ระวังดอย! มักเป็นจุดที่เจ้ามือจะเทขายใส่)

**💡 พอเห็นเลข "44 Fear" แบบนี้ เราต้องคิดยังไง?**
ถ้าเชื่อตามคำสอนของปู่ Warren Buffett ที่ว่า: **"จงกลัวเมื่อคนอื่นโลภ และจงโลภเมื่อคนอื่นกลัว"**

สถานะ **"Fear (44)"** แปลว่า ตลาดตอนนี้ซึมๆ คนไม่ค่อยกล้าเล่นครับ

- **มุมมองคนทั่วไป:** "อย่าเพิ่งยุ่งเลย เดี๋ยวราคาลงอีก"
- **มุมมองนักสวนกระแส (Contrarian):** "เริ่มน่าสนใจแล้ว เพราะราคาอาจจะถูกลงมาเยอะแล้ว"
        """)
else:
    st.warning("Unable to fetch Fear & Greed Index")

# Crypto News Center Sidebar
with st.sidebar:
    st.markdown("## 📰 Crypto News Center")
    st.markdown("Stay updated with the latest crypto news:")
    st.markdown("---")

    news_sites = [
        {"name": "CoinTelegraph", "url": "https://cointelegraph.com/"},
        {"name": "CoinDesk", "url": "https://www.coindesk.com/"},
        {"name": "The Block", "url": "https://www.theblock.co/"},
        {"name": "Decrypt", "url": "https://decrypt.co/"},
        {"name": "Bloomberg Crypto", "url": "https://www.bloomberg.com/crypto"}
    ]

    for site in news_sites:
        st.markdown(f"🔗 [{site['name']}]({site['url']})")

    st.markdown("---")
    st.markdown("*Click any link to read the latest news*")

    # Portfolio Calculator Section
    st.markdown("---")
    st.markdown("## 💼 My Portfolio")
    st.markdown("Calculate your total portfolio value:")

    # Input fields for portfolio
    btc_amount = st.number_input("Amount of BTC owned", min_value=0.0, value=0.0, step=0.01, format="%.4f")
    eth_amount = st.number_input("Amount of ETH owned", min_value=0.0, value=0.0, step=0.1, format="%.4f")
    gold_amount = st.number_input("Amount of Gold owned (oz)", min_value=0.0, value=0.0, step=0.1, format="%.2f")

# CSV file path
CSV_FILE = "crypto_prices.csv"

# Refresh button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 Refresh Data", type="primary"):
        st.rerun()

with col2:
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%H:%M:%S')}")

# Check if CSV file exists
if not os.path.exists(CSV_FILE):
    st.error(f"❌ Data file '{CSV_FILE}' not found. Please run tracker.py first.")
    st.stop()

# Read data from CSV
try:
    df = pd.read_csv(CSV_FILE)

    # Convert timestamp to datetime
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    # Get latest prices
    latest_btc = df['BTC Price'].iloc[-1]
    latest_eth = df['ETH Price'].iloc[-1]
    latest_gold = df['Gold Price'].iloc[-1] if 'Gold Price' in df.columns else 0

    # Calculate portfolio value and display in sidebar
    with st.sidebar:
        st.markdown("---")

        # Calculate total portfolio value
        btc_value = btc_amount * latest_btc
        eth_value = eth_amount * latest_eth
        gold_value = gold_amount * latest_gold
        total_value = btc_value + eth_value + gold_value

        # Display portfolio breakdown
        if total_value > 0:
            st.markdown(f"**BTC Value:** ${btc_value:,.2f}")
            st.markdown(f"**ETH Value:** ${eth_value:,.2f}")
            st.markdown(f"**Gold Value:** ${gold_value:,.2f}")
            st.markdown("---")
            st.markdown(f"<h2 style='text-align: center; color: #4CAF50; font-size: 2em;'>Total Portfolio Value<br>${total_value:,.2f}</h2>", unsafe_allow_html=True)
        else:
            st.info("Enter your holdings above to see your portfolio value")

    # Display metrics
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        btc_trend = df['BTC Trend'].iloc[-1] if 'BTC Trend' in df.columns else 'N/A'
        st.metric("💰 Bitcoin (BTC)", f"${latest_btc:,.2f}", delta=btc_trend)

    with col2:
        eth_trend = df['ETH Trend'].iloc[-1] if 'ETH Trend' in df.columns else 'N/A'
        st.metric("💎 Ethereum (ETH)", f"${latest_eth:,.2f}", delta=eth_trend)

    with col3:
        if 'Gold Price' in df.columns:
            gold_trend = df['Gold Trend'].iloc[-1] if 'Gold Trend' in df.columns else 'N/A'
            st.metric("🏆 Gold (GC=F)", f"${latest_gold:,.2f}", delta=gold_trend)

    # Display change metrics
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        btc_change = df['BTC Price'].iloc[-1] - df['BTC Price'].iloc[0]
        st.metric("BTC Change", f"${btc_change:,.2f}", delta=f"${btc_change:,.2f}")

    with col2:
        eth_change = df['ETH Price'].iloc[-1] - df['ETH Price'].iloc[0]
        st.metric("ETH Change", f"${eth_change:,.2f}", delta=f"${eth_change:,.2f}")

    with col3:
        if 'Gold Price' in df.columns:
            gold_change = df['Gold Price'].iloc[-1] - df['Gold Price'].iloc[0]
            st.metric("Gold Change", f"${gold_change:,.2f}", delta=f"${gold_change:,.2f}")

    # Display total data points
    st.markdown("---")
    st.markdown(f"**Total Data Points:** {len(df)} | **Time Range:** {df['Timestamp'].iloc[0]} to {df['Timestamp'].iloc[-1]}")

    # Section separator for charts
    st.markdown("---")
    st.markdown("## 📊 Price Trends Over Time with Moving Averages")
    st.markdown("*Teal line shows actual price | Coral line shows 10-period average*")

    # Calculate moving averages
    df['BTC_MA'] = df['BTC Price'].rolling(window=10, min_periods=1).mean()
    df['ETH_MA'] = df['ETH Price'].rolling(window=10, min_periods=1).mean()
    if 'Gold Price' in df.columns:
        df['Gold_MA'] = df['Gold Price'].rolling(window=10, min_periods=1).mean()

    # Get latest values for trend analysis
    latest_btc = df['BTC Price'].iloc[-1]
    latest_btc_ma = df['BTC_MA'].iloc[-1]
    latest_eth = df['ETH Price'].iloc[-1]
    latest_eth_ma = df['ETH_MA'].iloc[-1]

    # Create three columns for the charts
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 💰 Bitcoin (BTC)")

        # Create BTC chart
        fig_btc = go.Figure()
        fig_btc.add_trace(go.Scatter(
            x=df['Timestamp'],
            y=df['BTC Price'],
            mode='lines',
            name='Actual Price',
            line=dict(color='#5D9CEC', width=2)
        ))
        fig_btc.add_trace(go.Scatter(
            x=df['Timestamp'],
            y=df['BTC_MA'],
            mode='lines',
            name='10-Period MA',
            line=dict(color='#AAB2BD', width=2, dash='dash')
        ))
        fig_btc.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(x=0, y=1),
            xaxis_title="Time",
            yaxis_title="Price ($)"
        )
        st.plotly_chart(fig_btc, use_container_width=True)

        # BTC Analysis
        if latest_btc > latest_btc_ma:
            st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Strong Uptrend! 🚀 (Price is above average)</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Downtrend Warning ⚠️ (Price is below average)</div>", unsafe_allow_html=True)

        # Educational Expander
        with st.expander("ℹ️ 🎓 How to read this chart (Click to learn)"):
            st.write("**The Teal Line (Price):** Shows the current market price. Think of this as a 'Hyperactive Dog' running around.")
            st.write("**The Coral Line (Average):** Shows the 10-period average. Think of this as the 'Owner' walking steadily.")
            st.write("**Strategy:** If the Dog (Price) is significantly ABOVE the Owner (Average), the trend is strong, but it might pull back soon. If it's BELOW, the trend is weak.")

    with col2:
        st.markdown("#### 💎 Ethereum (ETH)")

        # Create ETH chart
        fig_eth = go.Figure()
        fig_eth.add_trace(go.Scatter(
            x=df['Timestamp'],
            y=df['ETH Price'],
            mode='lines',
            name='Actual Price',
            line=dict(color='#AC92EC', width=2)
        ))
        fig_eth.add_trace(go.Scatter(
            x=df['Timestamp'],
            y=df['ETH_MA'],
            mode='lines',
            name='10-Period MA',
            line=dict(color='#AAB2BD', width=2, dash='dash')
        ))
        fig_eth.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(x=0, y=1),
            xaxis_title="Time",
            yaxis_title="Price ($)"
        )
        st.plotly_chart(fig_eth, use_container_width=True)

        # ETH Analysis
        if latest_eth > latest_eth_ma:
            st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Strong Uptrend! 🚀 (Price is above average)</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Downtrend Warning ⚠️ (Price is below average)</div>", unsafe_allow_html=True)

        # Educational Expander
        with st.expander("ℹ️ 🎓 How to read this chart (Click to learn)"):
            st.write("**The Teal Line (Price):** Shows the current market price. Think of this as a 'Hyperactive Dog' running around.")
            st.write("**The Coral Line (Average):** Shows the 10-period average. Think of this as the 'Owner' walking steadily.")
            st.write("**Strategy:** If the Dog (Price) is significantly ABOVE the Owner (Average), the trend is strong, but it might pull back soon. If it's BELOW, the trend is weak.")

    with col3:
        if 'Gold Price' in df.columns:
            st.markdown("#### 🏆 Gold (GC=F)")

            latest_gold = df['Gold Price'].iloc[-1]
            latest_gold_ma = df['Gold_MA'].iloc[-1]

            # Create Gold chart
            fig_gold = go.Figure()
            fig_gold.add_trace(go.Scatter(
                x=df['Timestamp'],
                y=df['Gold Price'],
                mode='lines',
                name='Actual Price',
                line=dict(color='#F6BB42', width=2)
            ))
            fig_gold.add_trace(go.Scatter(
                x=df['Timestamp'],
                y=df['Gold_MA'],
                mode='lines',
                name='10-Period MA',
                line=dict(color='#AAB2BD', width=2, dash='dash')
            ))
            fig_gold.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                legend=dict(x=0, y=1),
                xaxis_title="Time",
                yaxis_title="Price ($)"
            )
            st.plotly_chart(fig_gold, use_container_width=True)

            # Gold Analysis
            if latest_gold > latest_gold_ma:
                st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Strong Uptrend! 🚀 (Price is above average)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white; font-weight: bold;'>Strategy: Downtrend Warning ⚠️ (Price is below average)</div>", unsafe_allow_html=True)

            # Educational Expander
            with st.expander("ℹ️ 🎓 How to read this chart (Click to learn)"):
                st.write("**The Teal Line (Price):** Shows the current market price. Think of this as a 'Hyperactive Dog' running around.")
                st.write("**The Coral Line (Average):** Shows the 10-period average. Think of this as the 'Owner' walking steadily.")
                st.write("**Strategy:** If the Dog (Price) is significantly ABOVE the Owner (Average), the trend is strong, but it might pull back soon. If it's BELOW, the trend is weak.")

    # AI Market Analyst Section
    st.markdown("---")
    st.markdown("")
    st.markdown("## 🤖 AI Market Analyst (Technical Analysis)")
    st.markdown("*Based on RSI (Relative Strength Index) with 7-period window*")

    # Calculate RSI for each asset
    btc_rsi = calculate_rsi(df['BTC Price'].values, period=7)
    eth_rsi = calculate_rsi(df['ETH Price'].values, period=7)
    gold_rsi = calculate_rsi(df['Gold Price'].values, period=7) if 'Gold Price' in df.columns else None

    # Display RSI values and signals
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 💰 Bitcoin (BTC)")
        if btc_rsi is not None:
            # Display RSI value with progress bar
            st.metric("RSI Value", f"{btc_rsi:.2f}")
            st.progress(btc_rsi / 100)

            # Display signal
            if btc_rsi > 70:
                st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white;'><strong>🟥 SELL Signal</strong><br>Overbought! (Price is too high/Expensive)</div>", unsafe_allow_html=True)
            elif btc_rsi < 30:
                st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white;'><strong>🟩 BUY Signal</strong><br>Oversold! (Price is cheap)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color: #AAB2BD; padding: 10px; border-radius: 5px; color: white;'><strong>⬜ Neutral</strong><br>Wait and See</div>", unsafe_allow_html=True)
        else:
            st.warning("Not enough data for RSI calculation")

    with col2:
        st.markdown("#### 💎 Ethereum (ETH)")
        if eth_rsi is not None:
            # Display RSI value with progress bar
            st.metric("RSI Value", f"{eth_rsi:.2f}")
            st.progress(eth_rsi / 100)

            # Display signal
            if eth_rsi > 70:
                st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white;'><strong>🟥 SELL Signal</strong><br>Overbought! (Price is too high/Expensive)</div>", unsafe_allow_html=True)
            elif eth_rsi < 30:
                st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white;'><strong>🟩 BUY Signal</strong><br>Oversold! (Price is cheap)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color: #AAB2BD; padding: 10px; border-radius: 5px; color: white;'><strong>⬜ Neutral</strong><br>Wait and See</div>", unsafe_allow_html=True)
        else:
            st.warning("Not enough data for RSI calculation")

    with col3:
        if 'Gold Price' in df.columns:
            st.markdown("#### 🏆 Gold (GC=F)")
            if gold_rsi is not None:
                # Display RSI value with progress bar
                st.metric("RSI Value", f"{gold_rsi:.2f}")
                st.progress(gold_rsi / 100)

                # Display signal
                if gold_rsi > 70:
                    st.markdown("<div style='background-color: #ED5565; padding: 10px; border-radius: 5px; color: white;'><strong>🟥 SELL Signal</strong><br>Overbought! (Price is too high/Expensive)</div>", unsafe_allow_html=True)
                elif gold_rsi < 30:
                    st.markdown("<div style='background-color: #48CFAD; padding: 10px; border-radius: 5px; color: white;'><strong>🟩 BUY Signal</strong><br>Oversold! (Price is cheap)</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='background-color: #AAB2BD; padding: 10px; border-radius: 5px; color: white;'><strong>⬜ Neutral</strong><br>Wait and See</div>", unsafe_allow_html=True)
            else:
                st.warning("Not enough data for RSI calculation")

    # Show raw data (optional)
    with st.expander("📊 View Raw Data"):
        st.dataframe(df.sort_values('Timestamp', ascending=False), use_container_width=True)

    # Statistics
    st.markdown("---")
    st.markdown("")
    st.markdown("## 📊 Statistics")

    if 'Gold Price' in df.columns:
        col1, col2, col3 = st.columns(3)
    else:
        col1, col2 = st.columns(2)
        col3 = None

    with col1:
        st.markdown("**Bitcoin (BTC)**")
        st.write(f"- Minimum: ${df['BTC Price'].min():,.2f}")
        st.write(f"- Maximum: ${df['BTC Price'].max():,.2f}")
        st.write(f"- Average: ${df['BTC Price'].mean():,.2f}")
        st.write(f"- Std Dev: ${df['BTC Price'].std():,.2f}")

    with col2:
        st.markdown("**Ethereum (ETH)**")
        st.write(f"- Minimum: ${df['ETH Price'].min():,.2f}")
        st.write(f"- Maximum: ${df['ETH Price'].max():,.2f}")
        st.write(f"- Average: ${df['ETH Price'].mean():,.2f}")
        st.write(f"- Std Dev: ${df['ETH Price'].std():,.2f}")

    if col3 is not None:
        with col3:
            st.markdown("**Gold (GC=F)**")
            st.write(f"- Minimum: ${df['Gold Price'].min():,.2f}")
            st.write(f"- Maximum: ${df['Gold Price'].max():,.2f}")
            st.write(f"- Average: ${df['Gold Price'].mean():,.2f}")
            st.write(f"- Std Dev: ${df['Gold Price'].std():,.2f}")

    # Market Radar - Top 10 Cryptocurrencies
    st.markdown("---")
    st.markdown("")
    st.markdown("## 🌍 Market Radar - Top 10 Cryptocurrencies by Market Cap")
    st.markdown("*Live data from CoinGecko API*")

    # Fetch and display top 10 cryptos
    top_10_df = fetch_top_10_cryptos()

    if top_10_df is not None:
        # Format the dataframe for display
        display_df = top_10_df.copy()

        # Add AI Signal column based on 24h change percentage
        def get_ai_signal(change_pct):
            if change_pct > 5:
                return '🚀 Strong Momentum'
            elif 0 <= change_pct <= 5:
                return '🟢 Uptrend'
            elif -5 <= change_pct < 0:
                return '🔴 Downtrend'
            else:  # < -5
                return '🩸 Panic Sell'

        # Apply AI Signal logic
        display_df['AI Signal'] = display_df['24h Change (%)'].apply(get_ai_signal)

        # Format currency and percentage columns
        display_df['Price ($)'] = display_df['Current Price'].apply(lambda x: f"${x:,.2f}")
        display_df['24h Change (%)'] = display_df['24h Change (%)'].apply(lambda x: f"{x:.2f}%")

        # Select and reorder columns for display
        display_df = display_df[['Name', 'Price ($)', '24h Change (%)', 'AI Signal']]

        # Function to color code the 24h change
        def highlight_change(row):
            try:
                change_val = float(row['24h Change (%)'].replace('%', ''))
                if change_val > 0:
                    color = 'background-color: #48CFAD'  # Mint green
                elif change_val < 0:
                    color = 'background-color: #ED5565'  # Soft rose
                else:
                    color = ''
                return [color if col == '24h Change (%)' else '' for col in row.index]
            except:
                return ['' for _ in row.index]

        # Apply styling
        styled_df = display_df.style.apply(highlight_change, axis=1)

        # Display the table
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.markdown("*Data updates every 5 minutes*")
    else:
        st.warning("Unable to fetch market data. Please try again later.")

except Exception as e:
    st.error(f"❌ Error reading data: {e}")
    st.info("Make sure the CSV file is properly formatted and contains data.")
