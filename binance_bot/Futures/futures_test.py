####################################################################
# import
####################################################################
import os
import sys
import logging
import pandas as pd
import asyncio

# 상위 폴더 파일 import를 위함
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import config as conf


from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from binance.error import ClientError
from binance.streams import AsyncClient, BinanceSocketManager
from datetime import datetime

####################################################################
# global values
####################################################################
#config_logging(logging, logging.DEBUG)

g_api_key = conf.G_API_KEY          # binance API key
g_secret_key = conf.G_SECRET_KEY    # binance secret key

####################################################################
# USD-M Futures connect
####################################################################
class UmFuture():
    def __init__(self):
        self.um_futures_client = UMFutures(key=g_api_key, secret=g_secret_key)       

    ####################################################################
    # change_leverage(self, symbol: str, leverage: int, **kwargs)
    # leverage 조정을 위한 메소드. 
    #
    # symbol:       coin symbol
    # leverage:     leverage value
    # recvWindow:   응답 대기시간(millisec)
    ####################################################################
    def change_leverage(self, coin_symbol, coin_leverage):
        try:
            response = self.um_futures_client.change_leverage(symbol=coin_symbol, leverage=coin_leverage, recvWindow=6000)
            #logging.info(response)
        except ClientError as error:
            logging.error("Found error. status: {}, error code: {}, error message: {}" 
            .format(error.status_code, error.error_code, error.error_message))

        return response

    ####################################################################
    # change_margin_type(self, symbol: str, marginType: str, **kwargs)
    # margin type을 변경하기 위한 메소드.
    #
    # symbol:       coin symbol
    # marginType:   CROSS or ISOLATED
    # recvWindow:   응답 대기시간(millisec)
    ####################################################################
    def change_margin_type(self, coin_symbol, margin_type):
        try:
            response = self.um_futures_client.change_margin_type(symbol=coin_symbol, marginType=margin_type, recvWindow=6000)
            #logging.info(response)
        except ClientError as error:
            if error.error_code != -4046:
                logging.error("Found error. status: {}, error code: {}, error message: {}" 
                .format(error.status_code, error.error_code, error.error_message))
        return response

    ####################################################################
    # account(self, **kwargs)
    # 잔고와 포지션을 조회하기 위한 메소드.
    #
    # recvWindow:   응답 대기시간(millisec)
    #
    # 포지션은 positionAmt 를 확인한다.(계약한 수량) long은 양수로, short는 음수로 나온다.
    ####################################################################
    def account_assets(self, asset_symbol: str):
        try:
            response = self.um_futures_client.account(recvWindow=6000)
            for i in response['assets']:
                if i['asset'] == asset_symbol:
                    return i

            #logging.info(response)
        except ClientError as error:
            if error.error_code != -4046:
                logging.error("Found error. status: {}, error code: {}, error message: {}" 
                .format(error.status_code, error.error_code, error.error_message))
        
        return response

    def account_positions(self, coin_symbol: str):
        try:
            response = self.um_futures_client.account(recvWindow=6000)
            for i in response['positions']:
                if i['symbol'] == coin_symbol:
                    return i

            #logging.info(response)
        except ClientError as error:
            if error.error_code != -4046:
                logging.error("Found error. status: {}, error code: {}, error message: {}" 
                .format(error.status_code, error.error_code, error.error_message))
        
        return response

    ####################################################################
    # account(self, **kwargs)
    # 잔고와 포지션을 조회하기 위한 메소드.
    #
    # recvWindow:   응답 대기시간(millisec)
    #
    # 포지션은 positionAmt 를 확인한다.(계약한 수량) long은 양수로, short는 음수로 나온다.
    ####################################################################
    def candles_info(self, coin_symbol: str, time_info: str, data_limit=500):    
        candles = self.um_futures_client.klines(symbol=coin_symbol, interval=time_info, limit=data_limit)
        open_time, close_time = [], []
        candle_open, candle_high, candle_low, candle_close, candle_volume =[], [], [], [], []
        
        df = pd.DataFrame(columns=['Open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time'])
        
        for candle in candles:
            open_time.append(datetime.fromtimestamp(int(candle[0]) / 1000))
            candle_open.append(float(candle[1]))
            candle_high.append(float(candle[2]))
            candle_low.append(float(candle[3]))
            candle_close.append(float(candle[4]))
            candle_volume.append(float(candle[5]))
            close_time.append(datetime.fromtimestamp(int(candle[6]) / 1000))

        df['Open_time'] = open_time
        df['Open'] = candle_open
        df['High'] = candle_high
        df['Low'] = candle_low
        df['Close'] = candle_close
        df['Volume'] = candle_volume
        df['Close_time'] = close_time
        df.set_index(['Open_time'], inplace=True)

        return df
    
    ####################################################################
    # book_ticker()
    # 호가창에 대한 정보
    #
    # 사용자 -> API를 이용한 데이터 요청 -> 거래소 -> 사용자의 요청 수신 -> 데이터 전달 -> 데이터 수신
    # 위 과정에서 오차가 발생할 수 있다. 
    # 문제를 해결하기 위해서 Websocket을 사용해야 한다.
    ####################################################################
    async def book_ticker_info(self, coin_symbol: str, response):
        client = await AsyncClient.create()
        manager = BinanceSocketManager(client)
        ts = manager.symbol_book_ticker_socket(coin_symbol)
        
        async with ts as res:
            while True:
                ret = await res.recv()
                response = ret
    
    async def run(self, response):
        await asyncio.wait([
            asyncio.ensure_future(self.book_ticker_info("BTCUSDT", response)),
        ])

um_future = UmFuture()

response = []
asyncio.run(um_future.run(response))
print(response)