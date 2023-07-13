import logging
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from binance.error import ClientError
import traceback
import pandas as pd
import numpy as np
import os
import time
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import util
import decorator
from consts import *

# 로그 내용을 파일로 만들려면 세번째 인자에 파일 명을 설정하면 된다.
config_logging(logging, logging.ERROR, "binance.log")

"""
recvWindow: API 요청을 보내는 시점과 Binance API 서버에서 요청을 처리하는 시점의 차이
"""

class Trader:
    """
    Trader
    """
    def __init__(self):
        self.binance = UMFutures(key=API_KEY, secret=API_SECRET)
        self.monitoring_flag = False
        self.position = None  # 현재 포지션
        self.entry_price = None # 진입 가격
        self.balance = None   # USDT 잔고
        self.new_order = None  # 접수 주문
        self.signal = False # 포지션 진입 조건 부합확인
        self.df_1h = pd.DataFrame(columns=['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'HA_Open', 'HA_High', 
                                           'HA_Low', 'HA_Close', 'HA_RSI', 'HA_EMA200', 'HA_STOCH_RSI_K', 'HA_STOCH_RSI_D'])  # 
        self.is_init_success = False  # 초기화함수 실행여부 확인변수
        self.init_data()  # 초기화 함수 실행

    def init_data(self):
        """
        트레이딩에 필요한 기능 초기화
        :return:
        """
        try:
            logging.info('init_data starts')
            # 초기화할 기능
            self.set_leverage()  # 레버리지 설정
            self.set_margin_type()  # 마진타입 설정
            self.get_new_order()  # 주문정보 조회
            self.get_balance_position()  # 잔고/포지션 조회
            self.is_init_success = True  # 초기화함수 완료
            util.send_to_telegram("init_data success")
        except Exception as e:
            util.send_to_telegram("❗️init_data got a error❗️")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())

    @decorator.call_binance_api
    def set_leverage(self):
        """
        레버리지 설정
        :return:
        """
        try:
            logging.info('set_leverage starts')
            res = self.binance.change_leverage(symbol=SYMBOL, leverage=LEVERAGE, recvWindow=6000)
            logging.info(res)
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    @decorator.call_binance_api
    def set_margin_type(self):
        """
        마진타입 설정
        :return:
        
        변경하려는 마진 타입이 기존설정과 동일한 경우, 아래와 같은 에러가 발생한다.
        "code":-4096, "msg":"No need to change margin Type."
        무시하고 넘어가도 된다.
        """
        try:
            logging.info('set_margin_type starts')
            res = self.binance.change_margin_type(symbol=SYMBOL, marginType=MARGIN_TYPE, recvWindow=6000)
            logging.info(res)
        except Exception as e:
            logging.error(traceback.format_exc())


    @decorator.call_binance_api
    def get_new_order(self):
        """
        미체결 주문조회
        :return:
        
        주문 정보를 얻어오는 과정.
        res 변수에는 과가 주문정보가 순서대로 들어있는 리스트.
        따라서 리스트의 마지막 인자 (res[len(res) - 1])에는 가장 최근에 접수한 주문이 있다.
        주문의 상태 값이 'NEW' 인지 확인해 조건에 해당하는 데이터가 있다면, 
        self.new_order 변수에 저장한다.

        sorted()
        __iterable: 정렬 할 데이터 리스트
        key: 정렬의 기준이 되는 값
        reverse: True 이면 내림차순

        key=lambda a: a['time']는 정렬 할 리스트 a의 time 값을 기준으로 정렬하겠다는 의미.

        """
        try:
            logging.info('get_new_order starts')
            res = self.binance.get_all_orders(symbol=SYMBOL, recvWindow=5000)
            ordered_res = sorted(res, key=lambda a: a['time'], reverse=True)
            filtered_res = list(filter(lambda a: a['status'] == 'NEW', ordered_res))
            self.new_order = filtered_res
            logging.info(self.new_order)
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())

    import numpy as np

    def calculate_stochastic_rsi(self, current_price, prev_price, prev_k, prev_d, prev_rsi, k_period, d_period):
        # Calculate RSI
        gain = max(current_price - prev_price, 0)
        loss = max(prev_price - current_price, 0)

        avg_gain = (prev_rsi + gain) / 1
        avg_loss = (prev_rsi + loss) / 1

        if avg_loss == 0:
            rs = 0
        else:
            rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))

        # Calculate Stochastic RSI
        min_rsi = min(prev_rsi, rsi)
        max_rsi = max(prev_rsi, rsi)

        stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)

        # Calculate K & D
        k = (prev_k + stoch_rsi) / 1
        d = (prev_d + k) / 1

        return k, d, rsi


    def calculate_ema(self, current_price, previous_ema, period):
        weight = 2 / (period + 1)
        ema = (current_price * weight) + (previous_ema * (1 - weight))
        return ema

    @decorator.call_binance_api
    def get_hourly_ha_candles(self):
        try:

            candles = self.binance.klines(SYMBOL, "1h", limit=4)
            opentime, lopen, lhigh, llow, lclose, lvol, closetime = [], [], [], [], [], [], []
            rsi_period = 14
            stoch_period = 14
            k_period = 3
            d_period = 3

            for candle in candles:
                opentime.append(datetime.fromtimestamp(int(candle[0]) / 1000))
                lopen.append(float(candle[1]))
                lhigh.append(float(candle[2]))
                llow.append(float(candle[3]))
                lclose.append(float(candle[4]))
                lvol.append(float(candle[5]))
                closetime.append(datetime.fromtimestamp(int(candle[6]) / 1000))
            
            if self.df_1h.empty:
                self.df_1h.loc[0] = {
                    'Open_time': BASE_CANDLE_DATA['Open_time'],
                    'Open': BASE_CANDLE_DATA['Open'],
                    'High': BASE_CANDLE_DATA['High'],
                    'Low': BASE_CANDLE_DATA['Low'],
                    'Close': BASE_CANDLE_DATA['Close'],
                    'Volume': BASE_CANDLE_DATA['Volume'],
                    'Close_time': BASE_CANDLE_DATA['Close_time'],
                    'HA_Open': BASE_CANDLE_DATA['HA_Open'],
                    'HA_Close': BASE_CANDLE_DATA['HA_Close'],
                    'HA_High': BASE_CANDLE_DATA['HA_High'],
                    'HA_Low': BASE_CANDLE_DATA['HA_Low'],
                    'HA_RSI': BASE_CANDLE_DATA['HA_RSI'],
                    'HA_EMA200': BASE_CANDLE_DATA['HA_EMA200'],
                    'HA_STOCH_RSI_K': BASE_CANDLE_DATA['HA_STOCH_RSI_K'],
                    'HA_STOCH_RSI_D':BASE_CANDLE_DATA['HA_STOCH_RSI_D']
                }
                print(self.df_1h)
                ha_open = []
                ha_high = []
                ha_low = []
                ha_close = []
                ha_ema200 = []
                ha_rsi = []
                ha_srsi_k = []
                ha_srsi_d = []

                for i in range(0, 4):
                    if i == 0:
                        ha_open.append(round((self.df_1h.iloc[-1]['HA_Open'] + self.df_1h.iloc[-1]['HA_Close']) / 2, 2))
                    else:
                        ha_open.append(round((ha_open[i-1] + ha_close[i-1]) / 2, 2))
                    ha_close.append(round((lopen[i] + lhigh[i] + llow[i] + lclose[i]) / 4, 2))
                    ha_high.append(round(max(ha_open[i], lhigh[i], ha_close[i]), 2))
                    ha_low.append(round(min(ha_open[i], llow[i], ha_close[i]), 2))

                for i in range(0, 4):
                    if i == 0:
                         # 현재 시점의 RSI 값을 계산하고 추가
                        # current_price, prev_price, prev_k, prev_d, prev_rsi, k_period, d_period
                        current_k, current_d, current_rsi = self.calculate_stochastic_rsi(ha_close[i], self.df_1h.iloc[-1]['HA_Close'], self.df_1h.iloc[-1]['HA_STOCH_RSI_K'], self.df_1h.iloc[-1]['HA_STOCH_RSI_D'], self.df_1h.iloc[-1]['HA_RSI'], k_period, d_period)
                        ha_srsi_k.append(current_k)
                        ha_srsi_d.append(current_d)
                        ha_rsi.append(current_rsi)
                        print(ha_srsi_k)
                        print(ha_srsi_d)
                        print(ha_rsi)
                        ha_ema200.append(self.calculate_ema(ha_close[i], self.df_1h.iloc[-1]['ema_200'], 200))
                        print(ha_ema200)
                    else:
                        current_k, current_d, current_rsi = self.calculate_stochastic_rsi(ha_close[i], ha_close[i-1], ha_srsi_k[i-1], ha_srsi_d[i-1], ha_rsi[i-1], k_period, d_period)
                        ha_srsi_k.append(current_k)
                        ha_srsi_d.append(current_d)
                        ha_rsi.append(current_rsi)
                        print(ha_srsi_k)
                        print(ha_srsi_d)
                        print(ha_rsi)

                        ha_ema200.append(self.calculate_ema(ha_close[i], ha_ema200[i-1], 200))
                        print(ha_ema200)

                new_row = pd.DataFrame(data={
                'Open_time': opentime,
                'Open': lopen,
                'High': lhigh,
                'Low': llow,
                'Close': lclose,
                'Volume': lvol,
                'Close_time': closetime,
                'HA_Open': ha_open,
                'HA_Close': ha_close,
                'HA_High': ha_high,
                'HA_Low': ha_low,
                'HA_RSI': ha_rsi,
                'HA_EMA200': ha_ema200,
                'HA_STOCH_RSI_K': ha_srsi_k,
                'HA_STOCH_RSI_D':ha_srsi_d
                })

                self.df_1h = pd.concat([self.df_1h, new_row], ignore_index=True)
                self.df_1h.set_index(['Open_time'], inplace=True)
                self.df_1h.sort_index(inplace=True)

                # self.df_1h['HA_Open'] = self.df_1h['HA_Open'].astype(float)
                # self.df_1h['HA_Close'] = self.df_1h['HA_Close'].astype(float)
                # self.df_1h['HA_High'] = self.df_1h['HA_High'].astype(float)
                # self.df_1h['HA_Low'] = self.df_1h['HA_Low'].astype(float)
            else:
                new_data = {
                    'Open_time': opentime[-1], 
                    'Open': lopen[-1], 
                    'High': lhigh[-1], 
                    'Low': llow[-1], 
                    'Close': lclose[-1], 
                    'Volume': lvol[-1], 
                    'Close_time': closetime[-1]
                    }
                
                if self.df_1h['Open_time'].iloc[-1] != new_data['Open_time']:
                    new_data['HA_Open'] = (self.df_1h.iloc[-1]['HA_Open'] + self.df_1h.iloc[-1]['HA_Close']) / 2
                    new_data['HA_Close'] = (new_data['Open'] + new_data['High'] + new_data['Low'] + new_data['Close']) / 4
                    new_data['HA_High'] = max(new_data['High'], new_data['HA_Open'], new_data['HA_Close'])
                    new_data['HA_Low'] = min(new_data['Low'], new_data['HA_Open'], new_data['HA_Close'])
                    
                    new_data['HA_RSI'] = self.calculate_current_rsi(self.df_1h.iloc[-1]['HA_RSI'], new_data['HA_Close'], rsi_period)
                     

                    current_k, current_d = self.calculate_current_stochastic_rsi(self.df_1h.iloc[-1]['HA_STOCH_RSI_K'], 
                                                                                     self.df_1h.iloc[-1]['HA_STOCH_RSI_D'], 
                                                                                     new_data['HA_RSI'], new_data['HA_Close'], 
                                                                                     rsi_period, stoch_period, k_period, d_period)
                    new_data['HA_STOCH_RSI_K'] = current_k
                    new_data['HA_STOCH_RSI_D'] = current_d

                    new_data['HA_EMA200'] = self.calculate_ema(new_data['HA_Close'], self.df_1h.iloc[-1]['HA_EMA200'], 200)

                    for i in range(2, -1, -1):
                        self.df_1h.iloc[i+1] = self.df_1h.iloc[i]
                    self.df_1h.iloc[3] = pd.Series(new_data)
                self.df_1h.set_index(['Open_time'], inplace=True)
                self.df_1h.sort_index(inplace=True)       

            print(self.df_1h)
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    """
    가장 최근 데이터와 이전 캔들이 200일 선 위에 있어야 함
    이전 봉의 데이터가 stoch rsi 20% 이하에 있어야 함
    k, d 가 골든 크로스 해야 함 (k 가 d 위로 가야 함)
    
    애초에 59분마다 모니터링 하도록 한다.
    위 조건에 부합했다면, 
    현재 봉 데이터가 밑 꼬리가 달리는지 확인.
    달리지 않는 봉에서 진입

    """
    def long_signal(self):
        above_ema = self.df_1h['HA_Close'][1] > self.df_1h['ema_200'][1]
        within_5_percent = self.df_1h['HA_Close'][1] < 1.03 * self.df_1h['ema_200'][1]
        stoch_rsi_below_20 = (self.df_1h['stoch_rsi_k'][1] < 20) and (self.df_1h['stoch_rsi_d'][1] < 20)
        golden_cross = self.df_1h['stoch_rsi_k'][1] > self.df_1h['stoch_rsi_d'][1] and self.df_1h['stoch_rsi_k'][2] <= self.df_1h['stoch_rsi_d'][2]
        no_lower_wick = self.df_1h['HA_Low'][0] == self.df_1h['HA_Open'][0]
        previous_candle_length = self.df_1h['HA_Close'][1] - self.df_1h['HA_Open'][1]
        current_candle_length = self.df_1h['HA_Close'][0] - self.df_1h['HA_Open'][0]
        next_candle_bullish = current_candle_length > previous_candle_length

        if above_ema and within_5_percent and stoch_rsi_below_20 and golden_cross:
            if no_lower_wick and next_candle_bullish:
                return True, True
            else:
                return False, True
        else:
            return False, False
    
    def short_signal(self):
        below_ema = self.df_1h['HA_Close'][1] < self.df_1h['ema_200'][1]
        within_5_percent = self.df_1h['HA_Close'][1] > 0.95 * self.df_1h['ema_200'][1]
        stoch_rsi_above_80 = (self.df_1h['stoch_rsi_k'][1] > 80) and (self.df_1h['stoch_rsi_d'][1] > 80)
        dead_cross = self.df_1h['stoch_rsi_k'][1] < self.df_1h['stoch_rsi_d'][1] and self.df_1h['stoch_rsi_k'][2] >= self.df_1h['stoch_rsi_d'][2]
        no_upper_wick = self.df_1h['HA_High'][0] == self.df_1h['HA_Open'][0]
        previous_candle_length = self.df_1h['HA_Open'][1] - self.df_1h['HA_Close'][1]
        current_candle_length = self.df_1h['HA_Open'][0] - self.df_1h['HA_Close'][0]
        next_candle_bearish = previous_candle_length < current_candle_length

        if below_ema and within_5_percent and stoch_rsi_above_80 and dead_cross:
            if next_candle_bearish and no_upper_wick:
                return True, True # 모든 조건에 충족하므로 바로 포지션 진입
            else:
                return False, True # 현재 캔들에 대한 조건이 충족하지 않아서 모니터링만 진행
        else: # 아무것도 부합하지 않음. 
            return False, False
        
    def long_signal_monitoring(self):
        no_lower_wick = self.df_1h['HA_Low'][0] == self.df_1h['HA_Open'][0]
        previous_candle_length = self.df_1h['HA_Close'][1] - self.df_1h['HA_Open'][1]
        current_candle_length = self.df_1h['HA_Close'][0] - self.df_1h['HA_Open'][0]
        next_candle_bullish = current_candle_length > previous_candle_length
        
        if no_lower_wick and next_candle_bullish:
            return True # 포지션 진입 조건 충족
        else:
            return False

    def short_signal_monitoring(self):
        no_upper_wick = self.df_1h['HA_High'][0] == self.df_1h['HA_Open'][0]
        previous_candle_length = self.df_1h['HA_Open'][1] - self.df_1h['HA_Close'][1]
        current_candle_length = self.df_1h['HA_Open'][0] - self.df_1h['HA_Close'][0]
        next_candle_bearish = previous_candle_length < current_candle_length
        
        if no_upper_wick and next_candle_bearish:
            return True # 포지션 진입 조건 충족
        else:
            return False

    def check_open_signal(self):
        signal = None
        print(self.df_1h['HA_Close'][2])
        print(self.df_1h['ema_200'][2])
        print(self.df_1h['HA_Close'][1])
        print(self.df_1h['ema_200'][1])
        candle_ema_loc = self.df_1h['HA_Close'][2] > self.df_1h['ema_200'][2] and self.df_1h['HA_Close'][1] > self.df_1h['ema_200'][1]

        if candle_ema_loc:
            signal = LONG
            return signal, self.long_signal() # True / False, True / False 
        else:
            signal = SHORT
            return signal, self.short_signal() # True / False, True / False

    @decorator.call_binance_api
    def handle_new_order(self):
        """
        주문체결 관리
        :return:

        1)포지션 오픈/종료 주문 > 2)체결 > 3)잔고 및 보유 포지션 정보 업데이트
        1)포지션 오픈/종료 주문 > 2)미체결 > 3)주문 취소 접수 > 3)잔고 및 보유 포지션 정보 업데이트

        손절주문 시, 30분 대기보다 바로 현재가격으로 손절하는 함수 필요

        origQty: 주문 접수수량
        executedQty: 주문 체결수량

        my_order[0]['origQty'] != my_order[0]['executedQty'] 일부만 체결된 경우, 처리 루틴도 필요하다.

        """
        try:
            logging.info('handle_new_order starts')
            res = self.binance.get_all_orders(symbol=SYMBOL, recvWindow=5000)
            my_order = list(filter(lambda a: a['orderId'] == self.new_order[0]['orderId'], res))
            logging.info(my_order)
            order_status = my_order[0]['status']
            order_time = my_order[0]['time']
            order_id = my_order[0]['orderId']

            # 체결 여부확인
            if order_status == 'FILLED':
                if my_order[0]['origQty'] == my_order[0]['executedQty']:
                    logging.info('order is filled')
                    util.send_to_telegram("order is filled")
                    self.new_order = None
                    self.get_balance_position()  # 잔고 및 포지션 변동 최신화

            # 취소 주문 후 취소여부 확인
            elif order_status == 'CANCELED':
                logging.info('order is canceled')
                util.send_to_telegram("order is canceled")
                self.new_order = None
                self.get_balance_position()  # 잔고 및 포지션 변동 최신화
        
            # 주문 상태가 계속해서 NEW(접수)
            else:
                # 취소 조건확인
                ordered_time = datetime.fromtimestamp(int(order_time) / 1000)
                now = datetime.now()
                diff = now - ordered_time
                min_after_order = divmod(diff.total_seconds(), 60)[0]  # float type
                # 주문체결 대기시간은 30분
                if min_after_order > 30:
                    cancel_res = self.binance.cancel_order(symbol=SYMBOL, orderId=order_id, recvWindow=5000)
                    util.send_to_telegram('order is going to be canceled')
                    logging.info('cancel_res')
                    logging.info(cancel_res)

        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    @decorator.call_binance_api
    def get_balance_position(self):
        """
        잔고/포지션 조회
        :return:

        res에는 각각 assets, positions라는 Key값을 갖고 있고 Key에 해당하는 값으로는 리스트.
        잔고조회는 assets을 확인.
        이 중에서 asset의 이름이 USDT인 자산을 필터링해(filter) res에 저장
        res_에 asset==USDT 조건을 만족하는 데이터를 list 형식으로 저장.
        res_는 리스트이기 때문에 res_[0]['availableBalance'] 와 같이 [0]이 필요.

        'availableBalance’가 바로 현재 사용가능한 잔고금액

        포지션을 필터링 할 때 주의할 점.
        res 에는 항상 데이터가 있다.
        res['positions']에는 현재 보유포지션이 있건 없건 항상 Binance 거래소에서 제공하는 거래 페어목록이 저장되어 있다.
        따라서 이 데이터들 중에서 실제로 보유중인 포지션을 구분하려면 'positionAmt'(보유수량) Key의 값이 있는지를 확인해야 한다.

        float(res[0]['positionAmt']) != 0 라는 의미는 LONG or SHORT 포지션이 존재한다는 의미
        res[0]['positionAmt']의 값이 양이면 LONG, 음수이면 SHORT
        """
        try:
            logging.info('get_balance_position starts')
            res = self.binance.account(recvWindow=6000)
            res_ = list(filter(lambda a: a['asset'] == 'USDT', res['assets']))
            self.balance = res_[0]['availableBalance']
            res = list(filter(lambda a: a['symbol'] == SYMBOL, res['positions']))
            self.position = res[0] if len(res) > 0 and float(res[0]['positionAmt']) != 0 else None
            # 포지션 롱/숏 구분
            if self.position and self.position['positionAmt']:
                self.position['current_side'] = LONG if float(self.position['positionAmt']) > 0 else SHORT
            logging.info(self.position)
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    @decorator.call_binance_api
    def open_position(self, signal):
        """
        포지션 오픈
        :return:

        qty = quantitiy(주문 수량)
        - 현재 이용 가능한 USDT 와 이용할 레버리지를 곱한 값을 주문 가격으로 나눔
        - 해당 값에 0.95를 곱하는데 이는 증거금 부족 에러 방지를 위함.
        - ETHUSDT 주문수량은 소수 세번째까지 된다. (다른 코인에 대해서는 확인 필요)

        현재 5분봉 캔들의 종가(close)는 현재가격이므로 close에 저장한 현재가격과 주문가격(order_price)를 비교
        주문가격은 최고매수/매도호가이기 때문에 현재가격과 큰 차이가 발생할 수 없지만, 금리발표 및 큰 호재/악재가 발생시에는 Binance
        API에서 받아온 호가와 실제 가격 차이가 큰 경우가 종종있다. 
        이렇게 순간적으로 가격의 급등락이 심할 때에는 트레이딩을 하지 않기 위해 넣은 조건
        
        주문수량이 0.004개 미만은 ETHUSDT의 최소주문수량을 충족시키지 못하기 때문에 Binance에서 주문접수를 거부

        """
        try:
            logging.info('open_position starts')
            res = self.binance.book_ticker(SYMBOL)
            # LONG 신호일 때 최고매도호가(askPrice)로 주문, SHORT 신호일 때 최고매수호가(bidPrice)로 주문
            order_price = float(res['askPrice']) if signal == LONG else float(res['bidPrice'])

            # margin insufficient 에러 방지를 위해 0.95 보정
            qty = float(self.balance) * LEVERAGE / order_price * 0.95
            qty = float(f"{qty:,.3f}")  # 소수 3째자리

            close = self.df_1h[-1:]['HA_Close'].values[0]
            # 주문가격과 현재 가격은 한호가 차이므로 큰 갭이 발생한다면 가격 급등락 때이므로 주문하지 않도록 함
            # 혹은 최소 주문 수량(0.004)보다 작다면 주문이 불가함
            if abs(order_price - close) > 5 or qty < 0.004:
                logging.info('stop open_position')
                return
            logging.info(order_price)
            logging.info(qty)
            order = self.binance.new_order(
                symbol=SYMBOL,
                side=SIGNAL_TO_OPEN_SIDE[signal],
                type="LIMIT",
                quantity=qty,
                timeInForce="GTC",
                price=order_price,
            )

            util.send_to_telegram("open_position is done")
            logging.info(order)
            self.new_order = []
            self.new_order.append(order)

        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())

    @decorator.call_binance_api
    def close_position(self):
        """
        포지션 종료
        :return:

        급등락 시, 수익이 아니라 손해라면, 그리고 손절 라인을 넘었다면, 
        무조건 종료하도록 하는 코드가 필요할 듯 하다.

        """
        try:
            logging.info('close_position starts')
            res = self.binance.book_ticker(SYMBOL)
            current_side = self.position['current_side']
            # 현재 LONG일 때 최고매수호가(bidPrice)로 주문, 현재 SHORT일 때 최고매도호가(askPrice)로 최대한 빨리 체결되도록 주문
            order_price = float(res['bidPrice']) if current_side == LONG else float(res['askPrice'])

            close = self.df_5m[-1:]['Close'].values[0]
            # 주문가격과 현재 가격은 한호가 차이므로 큰 갭이 발생한다면 가격 급등락 때이므로 주문하지 않도록 함
            if abs(order_price - close) > 5:
                logging.info('stop close_position')
                return
            logging.info(order_price)
            logging.info(self.position['positionAmt'])
            order = self.binance.new_order(
                symbol=SYMBOL,
                side=SIGNAL_TO_CLOSE_SIDE[current_side],
                type="LIMIT",
                quantity=abs(float(self.position['positionAmt'])),
                timeInForce="GTC",
                price=order_price,
            )

            util.send_to_telegram("close_position is done")
            logging.info(order)
            self.new_order = []
            self.new_order.append(order)

        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    def get_position_profit(self):
        """
        현재 진입포지션 수익률 계산
        :return:

        수익률 = (손익금액) / (투입금액) * 100
        """
        profit_percent = float(self.position['unRealizedProfit']) / float(self.position['isolatedWallet']) * 100
        return profit_percent
    

    def check_close_signal(self):
        """
        포지션 종료 조건 확인
        :return:
        """
        current_side = self.position['current_side']
        signal = None
        try:
            profit_percent = self.get_position_profit()

            if current_side == LONG:
                if profit_percent >= 3 or profit_percent <= -1.5:
                    signal = True
            elif current_side == SHORT:
                if profit_percent <= -3 or profit_percent >= 1.5:
                    signal = True
            else:
                return False  # 잘못된 position 값에 대해서 처리하지 않음

            if signal:  # 종료 확인 시 알림
                util.send_to_telegram("check_close_signal:ON")
            return signal
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())

    def run(self):
        if not self.is_init_success:
            logging.error('init_data got a error')
            return  # 초기화 비정상이면 프로그램

        logging.info('✅run starts')
        util.send_to_telegram("✅run starts")
        start_time = time.time()
        count = 0
        while True:
            try:
                self.get_hourly_ha_candles() # 캔들 데이터 수집

                if self.new_order:  # 접수 주문이 있는 경우
                    self.handle_new_order()  # 체결관리
                elif self.position:  # 보유 포지션이 있는 경우
                    time_diff = time.time() - start_time
                    if time_diff > 60 * 30:  # 30분마다 포지션 재확인(수동매매 대비)
                        start_time = time.time()
                        self.get_balance_position()

                    now = datetime.now()
                    if (now.minute == 0):
                        close_signal = self.check_close_signal()  # 포지션 종료체크
                        if close_signal:
                            self.close_position()  # 포지션 종료
                            self.signal = False
                            self.monitoring_flag = False

                else:  # 포지션이 없는 경우
                    now = datetime.now()
                    if (now.minute == 0):
                        # 포지션은 없지만, 모니터링을 해야 하는 경우
                        if self.signal == False and self.monitoring_flag:
                            if SHORT == self.position:
                                self.signal = self.short_signal_monitoring()
                                if self.signal:
                                    self.open_position(self.position)  # 포지션 오픈
                            else:
                                self.long_signal_monitoring()
                                if self.signal:
                                    self.open_position(self.position)  # 포지션 오픈

                        elif self.signal == False and self.monitoring_flag == False:
                            self.position, (self.signal, self.monitoring_flag) = self.check_open_signal()  # 포지션 오픈체크

                            if self.signal and self.monitoring_flag: # 현재 캔들이 조건 모두 충족으로 바로 포지션 오픈
                                self.open_position(self.position)  # 포지션 오픈

                
                time.sleep(LOOP_INTERVAL)
                count = count + 1
                
                if count == 60:
                    util.send_to_telegram("connecting..")
                    count = 0     


            except Exception as e:
                util.send_to_telegram("Program got a error")
                util.send_to_telegram(traceback.format_exc())
                logging.error(traceback.format_exc())




if __name__ == "__main__":
    try:
        if not API_KEY or not API_SECRET:
            logging.error('Set API_KEY and API_SECRET')
        else:
            util.send_to_telegram("Trader starts")
            trader = Trader()
            trader.run()
    except Exception as e:
        util.send_to_telegram("Program got a error")
        util.send_to_telegram(traceback.format_exc())
        logging.error(traceback.format_exc())
