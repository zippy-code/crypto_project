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

# 데이터 집합
df = pd.read_csv("./binance_bot/data/BTCUSDT.csv")

# 단순 이동평균 SMA
def get_sma(close, period):
    df_sma = SMAIndicator(close, window = period).sma_indicator()
    
    return df_sma

# 가중 이동평균 WMA
def get_wma(close, period):
    df_wma = WMAIndicator(close, window = period).wma()

    return df_wma

# 지수 이동평균 EMA
def get_ema(close, period):
    df_ema = EMAIndicator(close, window = period).ema_indicator()

    return  df_ema

# MACD 
def get_macd(close, period_slow, period_fast, period_sign):
    macd = MACD(close, window_slow = period_slow, window_fast = period_fast, window_sign = period_sign)

    # MACD line = 12d EMA - 26d EMA => DIF
    df_macd     = macd.macd()
    # Signal line = 9d EMA of MACD line => DEA
    df_macd_s   = macd.macd_signal()
    # MACD histogram = MACD line - signal line
    df_macd_d   = macd.macd_diff()

    # macd line 이 signal line 위에서 아래로 크로스 되면 데드 크로스
    # macd line 이 signal line 아래에서 위로 크로스 되면 골든 크로스

    return df_macd, df_macd_s, df_macd_d

# RSI
def get_rsi(close, period):
    df_rsi = RSIIndicator(close, window = period).rsi()

    return df_rsi

#StochRSI
def get_stochRSI(close, period, period_s1, period_s2):
    df_srsi = StochasticOscillator(close, window = period, smooth1 = period_s1, smooth2 = period_s2)

    return df_srsi

# Boliinger Bands
def get_bb(close, period, period_dev):
    bb = BollingerBands(close, window = period, window_dev = period_dev)

    df_bh = bb.bollinger_hband() # high band
    df_bhi = bb.bollinger_hband_indicator() # high band 보다 가격이 높으면 1, 아니면 0
    df_bl = bb.bollinger_lband() # low band
    df_bli = bb.bollinger_lband_indicator() # low band 보다 가격이 낮으면 1, 아니면 0
    df_bm = bb.bollinger_mavg # middle band
    df_bw = bb.bollinger_wband() # band width

    return df_bh, df_bhi, df_bl, df_bli, df_bm, df_bw

#VWAP
def get_vwap(high, low, close, vol, period):
    vwap = VolumeWeightedAveragePrice(high = high, low = low, close = close, volume = vol, window = period)
    df_vwmp = vwap.volume_weighted_average_price()

    return df_vwmp