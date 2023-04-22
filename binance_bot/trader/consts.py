import os

# BINANCE
API_KEY = os.getenv("BINANCE_API_KEY")  # TODO 반드시 설정해주세요
API_SECRET = os.getenv("BINANCE_SECRET_KEY")  # TODO 반드시 설정해주세요
# G_API_KEY = "sXowrrfuKRcscgr79eQm3NIiztBOukQEQaQr3w3knkocvsfpkzgHaIADu5s2IkzX"
# G_SECRET_KEY = "aSAsPz8am4Hf4ZlMcT34GrIocwk8UUSeyD9uNzZhA132jeyqmv5vCShqxiXQzphk"
# TRADING
SYMBOL = 'ETHUSDT'
LEVERAGE = 3
MARGIN_TYPE = 'ISOLATED'
LOOP_INTERVAL = 60 * 1  # 메인 루프 반복 시간(1분)
LOSS_CUT = -2  # 손절 라인
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

# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # TODO 반드시 설정해주세요
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # TODO 반드시 설정해주세요
TELEGRAM_MESSAGE_MAX_SIZE = 4095  # 텔레그램 메시지 최대길이