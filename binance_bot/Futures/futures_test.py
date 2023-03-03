####################################################################
# import
####################################################################
import os
import sys
import logging
import pandas as pd

# 상위 폴더 파일 import를 위함
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from common import config as conf


from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from binance.error import ClientError

####################################################################
# global values
####################################################################
#config_logging(logging, logging.DEBUG)

g_api_key = conf.G_API_KEY          # binance API key
g_secret_key = conf.G_SECRET_KEY    # binance secret key


####################################################################
# USD-M Futures connect
####################################################################
um_futures_client = UMFutures(key=g_api_key, secret=g_secret_key)

####################################################################
# change_leverage(self, symbol: str, leverage: int, **kwargs)
# leverage 조정을 위한 메소드. 
#
# symbol:       coin symbol
# leverage:     leverage value
# recvWindow:   응답 대기시간(millisec)
####################################################################
try:
    response = um_futures_client.change_leverage(symbol="BTCUSDT", leverage=4, recvWindow=6000)
    #logging.info(response)
except ClientError as error:
    logging.error("Found error. status: {}, error code: {}, error message: {}" 
    .format(error.status_code, error.error_code, error.error_message))

####################################################################
# change_margin_type(self, symbol: str, marginType: str, **kwargs)
# margin type을 변경하기 위한 메소드.
#
# symbol:       coin symbol
# marginType:   CROSS or ISOLATED
# recvWindow:   응답 대기시간(millisec)
####################################################################
try:
    response = um_futures_client.change_margin_type(symbol="BTCUSDT", marginType="ISOLATED", recvWindow=6000)
    #logging.info(response)
except ClientError as error:
    if error.error_code != -4046:
        logging.error("Found error. status: {}, error code: {}, error message: {}" 
        .format(error.status_code, error.error_code, error.error_message))

####################################################################
# account(self, **kwargs)
# 잔고와 포지션을 조회하기 위한 메소드.
#
# recvWindow:   응답 대기시간(millisec)
#
# 포지션은 positionAmt 를 확인한다.(계약한 수량) long은 양수로, short는 음수로 나온다.
####################################################################
try:
    response = um_futures_client.account(recvWindow=6000)
    for i in response['assets']:
        if i['asset'] == 'USDT':
            print(i)
    for i in response['positions']:
        if i['symbol'] == 'MKRUSDT':
            print(i)

    #logging.info(response)
except ClientError as error:
    if error.error_code != -4046:
        logging.error("Found error. status: {}, error code: {}, error message: {}" 
        .format(error.status_code, error.error_code, error.error_message))