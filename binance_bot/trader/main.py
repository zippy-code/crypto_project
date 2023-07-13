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
        self.position = None  # 현재 포지션
        self.entry_price = None # 진입 가격
        self.balance = None   # USDT 잔고
        self.new_order = None  # 접수 주문
        self.df_5m = pd.DataFrame(columns=['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time'])  # 5분봉
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
    def open_position_by_signal(self, signal_result, signal_type):
        if signal_result:
            logging.info('open_position starts')
            index, self.entry_price = signal_result[1], signal_result[2]

            res = self.binance.book_ticker(SYMBOL)
            ask_price = float(res['askPrice'])
            bid_price = float(res['bidPrice'])
            order_price = ask_price if signal_type == LONG else bid_price

            # margin insufficient 에러 방지를 위해 0.95 보정
            qty = float(self.balance) * LEVERAGE / order_price * 0.95
            qty = float(f"{qty:,.3f}")  # 소수 3째자리

            close = self.df_5m[-1:]['Close'].values[0]

            # 주문가격과 현재 가격이 큰 차이가 발생한다면 가격 급등락 때이므로 주문하지 않도록 함
            # 혹은 최소 주문 수량(0.004)보다 작다면 주문이 불가함
            if abs(order_price - close) > 5 or qty < 0.004:
                logging.info('stop open_position')
                return
            logging.info(order_price)
            logging.info(qty)
            order = self.binance.new_order(
                symbol=SYMBOL,
                side=SIGNAL_TO_OPEN_SIDE[signal_type],
                type="LIMIT",
                quantity=qty,
                timeInForce="GTC",
                price=entry_price,  # 미리 계산된 롱/숏 포지션 진입 가격
            )

            util.send_to_telegram("open_position is done")
            logging.info(order)
            self.new_order = []
            self.new_order.append(order)

    def check_close_signal_by_profit_loss(self, entry_price, current_price, fee_rate=0.00075):
        take_profit_percentage = 0.03
        stop_loss_percentage = 0.015

        current_side = self.position['current_side']
        entry_price = self.entry_price

        pnl = (current_price / entry_price - 1) if current_side == LONG else (entry_price / current_price - 1)
        pnl -= fee_rate * 2  # 반영된 수수료 차감

        if pnl >= take_profit_percentage or pnl <= -stop_loss_percentage:
            util.send_to_telegram("check_close_signal_by_profit_loss:ON")
            return True
        return False
    

    @decorator.call_binance_api
    def get_price(self):
        '''
        5분봉 데이터 조회
        :return:
        '''
        try:

            candles = self.binance.klines(SYMBOL, "5m", limit=1000)
            opentime, lopen, lhigh, llow, lclose, lvol, closetime = [], [], [], [], [], [], []

            for candle in candles:
                opentime.append(datetime.fromtimestamp(int(candle[0]) / 1000))
                lopen.append(float(candle[1]))
                lhigh.append(float(candle[2]))
                llow.append(float(candle[3]))
                lclose.append(float(candle[4]))
                lvol.append(float(candle[5]))
                closetime.append(datetime.fromtimestamp(int(candle[6]) / 1000))

            self.df_5m['Open_time'] = opentime
            self.df_5m['Open'] = lopen
            self.df_5m['High'] = lhigh
            self.df_5m['Low'] = llow
            self.df_5m['Close'] = lclose
            self.df_5m['Volume'] = lvol
            self.df_5m['Close_time'] = closetime
            self.df_5m.set_index(['Open_time'], inplace=True)

            self.df_5m['ma20'] = self.df_5m['Close'].rolling(window=20).mean()  # 20일 이동평균값
            self.df_5m['upper_band'] = self.df_5m['ma20'] + 2 * self.df_5m['Close'].rolling(window=20).std()  # BB(볼린저밴드) 상단 밴드
            self.df_5m['lower_band'] = self.df_5m['ma20'] - 2 * self.df_5m['Close'].rolling(window=20).std()  # BB(볼린저밴드) 하단 밴드# %b = (종가 - 하단 볼린저 밴드) / (상단 볼린저 밴드 - 하단 볼린저 밴드)
            self.df_5m['band_b'] = (self.df_5m['Close'] - self.df_5m['lower_band']) / (self.df_5m['upper_band'] - self.df_5m['lower_band'])  # BB(볼린저밴드) %b
        except Exception as e:
            util.send_to_telegram("Program got a error")
            util.send_to_telegram(traceback.format_exc())
            logging.error(traceback.format_exc())


    def check_open_signal(self):
        """
        포지션 오픈 조건확인
        :return:

        현재 캔들의 band_b를 조회하려면
        print(self.df_5m[-1:]['band_b'].values[0])
        """
        signal = None
        try:
            band_b = self.df_5m[-1:]['band_b'].values[0]
            if band_b > 1.3:  # %B가 1.3 이상인 경우 숏포지션 오픈
                signal = SHORT
            elif band_b < -0.3:  # %B가 -0.3 이하인 경우 롱포지션 오픈
                signal = LONG

            if signal:  # 오픈 시그널확인시 알림
                util.send_to_telegram("check_open_signal:{}".format(signal))

            return signal
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

            close = self.df_5m[-1:]['Close'].values[0]
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

    def check_close_signal(self):
        """
        포지션 종료 조건확인
        :return:
        """
        current_side = self.position['current_side']
        signal = None
        try:
            band_b = self.df_5m[-1:]['band_b'].values[0]
            if current_side == LONG and band_b > 0:  # 현재 롱포지션이면서 %B가 0 이상인 경우 종료
                signal = True
            elif current_side == SHORT and band_b < 1:  # 현재 숏포지션이면서 %B가 1 이하인 경우 종료
                signal = True
            elif self.get_position_profit() <= LOSS_CUT:
                signal = True

            if signal:  # 정려 확인시 알림
                util.send_to_telegram("check_close_signal:ON")
            return signal
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

    def run(self):
        """
        프로그램 메인함수
        :return:

        아래 각각의 프로세스는 개별적으로 진행
        세 가지 케이스가 각각 따로 처리되며 동시에 일어날 수 없음

        보유 포지션이 없는 경우
        1)포지션 오픈조건 확인 > 2)포지션 오픈조건 충족 > 3)포지션 오픈 주문 접수 > 4)주문 체결관리
        
        보유 포지션이 있는 경우
        1)포지션 종료조건 확인 > 2)포지션 종료조건 충족 > 3)포지션 종료 주문 접수 > 4)주문 체결관리

        접수한 주문이 있는 경우
        1)미체결 주문 존재 > 2)체결 or 미체결로 취소
        """
        if not self.is_init_success:
            logging.error('init_data got a error')
            return  # 초기화 비정상이면 프로그램

        logging.info('✅run starts')
        util.send_to_telegram("✅run starts")
        start_time = time.time()
        count = 0
        while True:
            try:
                self.get_price()  # 5분봉 데이터 조회

                if self.new_order:  # 접수 주문이 있는 경우
                    self.handle_new_order()  # 체결관리
                elif self.position:  # 보유 포지션이 있는 경우
                    time_diff = time.time() - start_time
                    if time_diff > 60 * 30:  # 30분마다 포지션 재확인(수동매매 대비)
                        start_time = time.time()
                        self.get_balance_position()

                    close_signal = self.check_close_signal()  # 포지션 종료체크
                    if close_signal:
                        self.close_position()  # 포지션 종료
                else:  # 포지션이 없는 경우
                    open_signal = self.check_open_signal()  # 포지션 오픈체크
                    if open_signal:
                        self.open_position(open_signal)  # 포지션 오픈

                #
                #util.send_to_telegram("connecting.. and band_b:{}".format(band_b))
                # 루프 대기 시간(* 1분)
                # 매 루프마다 1분씩 sleep -> 보유 포지션이 없어서 포지션 오픈 조건을 확인할 경우
                # 너무 많은 Binance API 호출을 하여 사용의 제한이 걸릴 수도 있기 때문.
                # 5분봉 데이터를 사용하기 때문에 1분 주기로 포지션 오픈/종료 조건을 체크하는 것에 무리가 없다.
                time.sleep(LOOP_INTERVAL)
                count = count + 1
                
                if count == 60:
                    band_b = self.df_5m[-1:]['band_b'].values[0]
                    util.send_to_telegram("connecting.. and band_b:{}".format(band_b))
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
