import pandas as pd
import ta
from binance.client import Client
import requests
import time
from datetime import datetime
import os
import platform
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY =os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY =os.getenv('BINANCE_SECRET_KEY')
TELEGRAM_TOKEN  =os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID =os.getenv('TELEGRAM_CHAT_ID')


# 🔐 API KEYS (Replace these with your actual keys)


# ⚙️ Config
SYMBOL = 'BTCUSDT'
HIGHER_TF = '1h'
LOWER_TF = '15m'
LIMIT = 100

# Binance Client
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=data)
    def play_alarm():
        system = platform.system()
        if system == 'Windows':
            os.system('start alarm.mp3')
        elif system == 'Darwin':  # macOS
            os.system('afplay alarm.mp3')
        else:  # Linux
            os.system('mpg123 alarm.mp3')
    play_alarm()

def get_klines(symbol, interval, limit=100):
    data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def apply_indicators(df):
    df['EMA20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    return df

# ✅ Bullish Candlestick Patterns
def detect_bullish_patterns(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    bullish_engulfing = (prev['close'] < prev['open']) and (last['close'] > last['open']) and \
                        (last['open'] < prev['close']) and (last['close'] > prev['open'])

    hammer = (last['close'] > last['open']) and ((last['low'] < last['open']) and 
              ((last['open'] - last['low']) > 2 * (last['close'] - last['open'])))

    morning_star = (df.iloc[-3]['close'] < df.iloc[-3]['open']) and \
                   (abs(df.iloc[-2]['close'] - df.iloc[-2]['open']) < (df['close'].max() * 0.002)) and \
                   (last['close'] > df.iloc[-3]['open'])

    piercing_line = (prev['close'] < prev['open']) and (last['close'] > last['open']) and \
                    (last['open'] < prev['close']) and (last['close'] > (prev['open'] + prev['close']) / 2)
    
        # Extra patterns
    doji = abs(last['close'] - last['open']) < ((last['high'] - last['low']) * 0.1)
    inverted_hammer = (last['close'] > last['open']) and ((last['high'] - last['close']) > 2 * (last['close'] - last['open']))
    
    three_white_soldiers = (
        df.iloc[-3]['close'] > df.iloc[-3]['open'] and
        df.iloc[-2]['close'] > df.iloc[-2]['open'] and
        last['close'] > last['open'] and
        df.iloc[-3]['close'] < df.iloc[-2]['close'] < last['close']
    )

    return bullish_engulfing or hammer or morning_star or piercing_line or doji or inverted_hammer or three_white_soldiers


# ⚠️ Crash Detection
def detect_crash(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    red_candle = (last['close'] < last['open']) and (last['open'] - last['close']) > ((last['high'] - last['low']) * 0.6)
    rsi_drop = df['RSI'].iloc[-1] < 30
    bearish_engulfing = (prev['close'] > prev['open']) and (last['close'] < last['open']) and \
                        (last['open'] > prev['close']) and (last['close'] < prev['open'])
    return red_candle and rsi_drop or bearish_engulfing

# 💸 Entry Levels
def calculate_trade_levels(entry_price, atr):
    risk_amount = 0.10
    tp_price = entry_price * 1.02
    sl_price = entry_price - atr if atr < risk_amount else entry_price - risk_amount
    return round(tp_price, 2), round(sl_price, 2)

# 🧠 Analysis
def analyze():
    df_high = get_klines(SYMBOL, HIGHER_TF, LIMIT)
    df_low = get_klines(SYMBOL, LOWER_TF, LIMIT)

    df_high = apply_indicators(df_high)
    df_low = apply_indicators(df_low)

    signal = ""
    crash = False

    ema20 = df_high['EMA20'].iloc[-1]
    ema50 = df_high['EMA50'].iloc[-1]
    rsi_high = df_high['RSI'].iloc[-1]
    volume_now = df_low['volume'].iloc[-1]
    volume_avg = df_low['volume'].mean()
    bullish = detect_bullish_patterns(df_low)

    print(f"💡 EMA20: {ema20:.2f}, EMA50: {ema50:.2f}, RSI: {rsi_high:.2f}")
    print(f"🔊 Volume: {volume_now:.2f} vs Avg: {volume_avg:.2f}, Bullish Pattern: {bullish}")

    if ema20 > ema50 and rsi_high > 45:
        if bullish and volume_now > 0.8 * volume_avg:
            signal = "BUY"

    if detect_crash(df_low):
        crash = True

    return signal, crash, df_high.iloc[-1], df_low.iloc[-1], df_low['ATR'].iloc[-1]

# 💞 Main Bot
def main():
    print("🚀 Binance Buy Bot Running with Crash Detection 💘")
    while True:
        try:
            print("Looking for signals")
            signal, crash, high_info, low_info, atr = analyze()
            entry_price = low_info['close']
            tp_price, sl_price = calculate_trade_levels(entry_price, atr)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if signal == "BUY":
                message = f"""📈 <b>BUY Signal!</b>
<b>Time:</b> {now}
<b>Symbol:</b> {SYMBOL}
<b>Entry:</b> {entry_price} USD
<b>TP:</b> {tp_price} USD (2%)
<b>SL:</b> {sl_price} USD (ATR-based or $0.10)
<b>High TF:</b> RSI {high_info['RSI']:.2f}, EMA20: {high_info['EMA20']:.2f} > EMA50: {high_info['EMA50']:.2f}
🕯️ Bullish Pattern & Volume Spike
"""
                send_telegram_message(message)
                print("💌 BUY SIGNAL SENT")

            if crash:
                message = f"""⚠️ <b>CRASH ALERT</b>
<b>Time:</b> {now}
<b>Symbol:</b> {SYMBOL}
🚨 Red candle detected and RSI breakdown.
💔 Stay cautious, market might drop fast.
"""
                send_telegram_message(message)
                print("⚠️ Crash warning sent")

            time.sleep(300)

        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
