import time
import datetime
import pandas as pd
import requests

def get_date(milli_time):
    KST = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.fromtimestamp(milli_time / 1000.0, tz=KST)
    timeline = str(dt.strftime('%D %H:%M:%S'))
    return timeline

# limit=1440 은 하루가 1440 분이기 때문이다.
base_url="https://www.binance.com/fapi/v1/continuousKlines?pair=BTCUSDT&contractType=PERPETUAL&interval=1m&limit=1440&startTime={}"
gettimestamp = int(time.time() - 60 * 60 * 24 * 120) * 1000 # 120일 간 데이터를 얻기 위해 시간 설정

df_candle = pd.DataFrame()

for i in range(120):
    url = base_url.format(int(gettimestamp))
    webpage = requests.get(url)

    df_candle_temp = pd.read_json(webpage.content)

    df_candle = pd.concat([df_candle, df_candle_temp], axis = 0)
    gettimestamp = df_candle_temp[0][-1:].values[0]

rename_columns = {0: 'time', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}
df_candle = df_candle[[0, 1, 2, 3, 4, 5]].rename(columns=rename_columns)

df_candle = df_candle.dropna(axis = 0)

df_candle['time'] = df_candle['time'].apply(get_date)

df_candle.to_csv("./binance_bot/data/BTCUSDT.csv", index = False)
