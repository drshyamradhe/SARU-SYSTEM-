import streamlit as st
import yfinance as yf
import pandas as pd
import ta

st.set_page_config(page_title="SARU SYSTEM", layout="wide")

# App Header
st.title("SARU SYSTEM")
st.markdown("---")

# ---------------------------------------------------------
# 1. TOP SPOT PRICES (Nifty, BankNifty, DXY, Crude, Gold)
# ---------------------------------------------------------
st.subheader("Global & Market Spot Prices")

tickers = {
    "Nifty Spot": "^NSEI",
    "BankNifty Spot": "^NSEBANK",
    "DXY Spot": "DX-Y.NYB",
    "Crude Oil Spot": "CL=F",
    "Gold Spot": "GC=F"
}

cols = st.columns(len(tickers))

for col, (label, symbol) in zip(cols, tickers.items()):
    try:
        data = yf.Ticker(symbol).history(period="2d")
        if len(data) >= 2:
            current_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2]
            change = current_price - prev_price
            pct_change = (change / prev_price) * 100
            col.metric(
                label=label, 
                value=f"{current_price:,.2f}", 
                delta=f"{change:+.2f} ({pct_change:+.2f}%)"
            )
        elif len(data) == 1:
            current_price = data['Close'].iloc[-1]
            col.metric(label=label, value=f"{current_price:,.2f}")
        else:
            col.metric(label=label, value="N/A")
    except Exception:
        col.metric(label=label, value="Error")

st.markdown("---")

# ---------------------------------------------------------
# 2. NIFTY FUTURES & OPTIONS STOCKS (Top 5 Gainers & Losers)
# ---------------------------------------------------------
st.subheader("Nifty Futures & Options Stocks")

# Representative list of major Nifty F&O stocks (NSE tickers with '.NS')
FO_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LTIM.NS", "LT.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "NTPC.NS",
    "POWERGRID.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS"
]

@st.cache_data(ttl=300)
def fetch_fo_performance(stock_list):
    results = []
    for ticker in stock_list:
        try:
            df = yf.Ticker(ticker).history(period="2d")
            if len(df) >= 2:
                close = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                pct_chg = ((close - prev) / prev) * 100
                results.append({
                    "Symbol": ticker.replace(".NS", ""),
                    "Price": round(close, 2),
                    "% Change": round(pct_chg, 2)
                })
        except Exception:
            pass
    return pd.DataFrame(results)

with st.spinner("Fetching F&O Market Gainers and Losers..."):
    df_fo = fetch_fo_performance(FO_STOCKS)

if not df_fo.empty:
    top_5_gainers = df_fo.sort_values(by="% Change", ascending=False).head(5)
    top_5_losers = df_fo.sort_values(by="% Change", ascending=True).head(5)

    g_col, l_col = st.columns(2)

    with g_col:
        st.markdown("### Top 5 Gainers")
        st.dataframe(top_5_gainers, hide_index=True, use_container_width=True)

    with l_col:
        st.markdown("### Top 5 Losers")
        st.dataframe(top_5_losers, hide_index=True, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 3. SCREENING CRITERIA
# ---------------------------------------------------------
st.subheader("Screening Criteria")

st.info("""
**Buy Stocks Logic:**
* Current Price > 200-day SMA
* Buy Signal Generated if **Bullish Crossover** of 50 SMA & 200 SMA occurs on 1-Hour candles.

**Sell Stocks Logic:**
* Current Price < 200-day SMA
* Sell Signal Generated if **Bearish Crossover** of 50 SMA & 200 SMA occurs on 1-Hour candles.
""")

@st.cache_data(ttl=600)
def run_screener(stock_list):
    buy_list = []
    sell_list = []
    
    for ticker in stock_list:
        try:
            # Fetch 1-hour interval data for technical indicators
            stock = yf.Ticker(ticker)
            df_hourly = stock.history(period="60d", interval="1h")
            
            if len(df_hourly) < 200:
                continue
            
            # Calculate Moving Averages on hourly data
            df_hourly['SMA_50'] = ta.trend.sma_indicator(df_hourly['Close'], window=50)
            df_hourly['SMA_200'] = ta.trend.sma_indicator(df_hourly['Close'], window=200)
            
            current_price = df_hourly['Close'].iloc[-1]
            sma_50_curr = df_hourly['SMA_50'].iloc[-1]
            sma_200_curr = df_hourly['SMA_200'].iloc[-1]
            
            sma_50_prev = df_hourly['SMA_50'].iloc[-2]
            sma_200_prev = df_hourly['SMA_200'].iloc[-2]
            
            symbol_clean = ticker.replace(".NS", "")
            
            # Buy Signal: Price > 200 SMA AND (50 SMA crossed above 200 SMA)
            bullish_crossover = (sma_50_prev <= sma_200_prev) and (sma_50_curr > sma_200_curr)
            if current_price > sma_200_curr and bullish_crossover:
                buy_list.append({
                    "Symbol": symbol_clean,
                    "Price": round(current_price, 2),
                    "50 SMA": round(sma_50_curr, 2),
                    "200 SMA": round(sma_200_curr, 2),
                    "Signal": "BUY"
                })
            
            # Sell Signal: Price < 200 SMA AND (50 SMA crossed below 200 SMA)
            bearish_crossover = (sma_50_prev >= sma_200_prev) and (sma_50_curr < sma_200_curr)
            if current_price < sma_200_curr and bearish_crossover:
                sell_list.append({
                    "Symbol": symbol_clean,
                    "Price": round(current_price, 2),
                    "50 SMA": round(sma_50_curr, 2),
                    "200 SMA": round(sma_200_curr, 2),
                    "Signal": "SELL"
                })
                
        except Exception:
            continue
            
    return pd.DataFrame(buy_list), pd.DataFrame(sell_list)

if st.button("Run Screener"):
    with st.spinner("Scanning 1-Hour Candles & Moving Average Crossovers..."):
        buy_df, sell_df = run_screener(FO_STOCKS)
        
        b_col, s_col = st.columns(2)
        with b_col:
            st.markdown("#### Buy Signals")
            if not buy_df.empty:
                st.dataframe(buy_df, hide_index=True, use_container_width=True)
            else:
                st.write("No Buy signals detected.")

        with s_col:
            st.markdown("#### Sell Signals")
            if not sell_df.empty:
                st.dataframe(sell_df, hide_index=True, use_container_width=True)
            else:
                st.write("No Sell signals detected.")
