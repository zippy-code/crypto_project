# TA는 판다스 패키지를 기반으로 개발 됨.
# 기술 지표는 대부분 시간, 고가, 저가, 종가, 거래량을 기본 데이터로 계산한다.
# URL: https://technical-analysis-library-in-python.readthedocs.io/en/latest

import pandas as pd
import numpy as np
from ta.trend import SMAIndicator
from ta.trend import WMAIndicator
from ta.trend import EMAIndicator
from ta.trend import MACD
from ta.momentum import RSIIndicator 
from ta.momentum import StochasticOscillator
from ta.volatility import BollingerBands
from ta.volume import VolumeWeightedAveragePrice



df = pd.read_csv("./binance_bot/data/BTCUSDT.csv")