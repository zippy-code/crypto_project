import os
from datetime import datetime

# BINANCE
API_KEY = os.getenv("BINANCE_API_KEY")  # TODO 반드시 설정해주세요
API_SECRET = os.getenv("BINANCE_SECRET_KEY")  # TODO 반드시 설정해주세요
# G_API_KEY = "sXowrrfuKRcscgr79eQm3NIiztBOukQEQaQr3w3knkocvsfpkzgHaIADu5s2IkzX"
# G_SECRET_KEY = "aSAsPz8am4Hf4ZlMcT34GrIocwk8UUSeyD9uNzZhA132jeyqmv5vCShqxiXQzphk"
# TRADING
SYMBOL = 'ETHUSDT'
LEVERAGE = 8
MARGIN_TYPE = 'ISOLATED'
LOOP_INTERVAL = 60 * 1  # 메인 루프 반복 시간(1분)
LOSS_CUT = -5  # 손절 라인
LONG = 'LONG'
SHORT = 'SHORT'

# 주문관련
SIGNAL_TO_OPEN_SIDE = {
    LONG: 'BUY',
    SHORT: 'SELL'
}

SIGNAL_TO_CLOSE_SIDE = {
    LONG: 'SELL',
    SHORT: 'BUY'
}

BASE_CANDLE_DATA = {'Open_time': datetime(2023, 7, 18, 0, 0), 
                    'Open': 1872.55, 
                    'High': 1883.44, 
                    'Low': 1872.47, 
                    'Close': 1882.12, 
                    'Volume': 0, 
                    'Close_time': datetime(2023, 7, 13, 18, 59, 59, 999000),
                    'HA_Open': 1870.48,
                    'HA_Close': 1877.65,
                    'HA_High': 1883.44,
                    'HA_Low': 1870.48,
                    'HA_RSI': 54.53,
                    'HA_EMA200': 1887.34,
                    'HA_STOCH_RSI_K': 82.74,
                    'HA_STOCH_RSI_D':58.45
                    }
# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # TODO 반드시 설정해주세요
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # TODO 반드시 설정해주세요
TELEGRAM_CHAT_ID = "-1001762270002"
TELEGRAM_MESSAGE_MAX_SIZE = 4095  # 텔레그램 메시지 최대길이