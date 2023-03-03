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
binance_btc_url="https://www.binance.com/fapi/v1/continuousKlines?pair=BTCUSDT&contractType=PERPETUAL&interval=1m&limit=1440&startTime={}"
# time.time() 함수는 현재 시각을 초 단위 
gettimestamp = int(time.time() - 60 * 60 * 24 * 120) * 1000 
df_candle = pd.DataFrame()

for i in range(int(120*1.4)):
    # 시간 값을 적용
    url = binance_btc_url.format(int(gettimestamp))
    webpage = requests.get(url)
    # 최신 pandas 에서 read_json() 을 사용할 경우, byte type 관련 에러가 나온다. 이때 .decode()를 사용하면 str 형태로 변경가능하다.
    df_candle_temp = pd.read_json((webpage.content).decode())
    df_candle = pd.concat([df_candle, df_candle_temp], axis=0)

    # df_candle_temp[0][-1:] 까지는 df_candle_temp 데이터 프레임의 0번째 컬럼, 마지막 값을 의미하고, values[0]는 index 값을 제거하고 순수하게 column 값만 반환한다.
    gettimestamp = df_candle_temp[0][-1:].values[0]

# 컬럼의 이름을 변경하는 루틴
rename_columns = {0:'Time', 1: 'Open', 2: 'High', 3: 'Low', 4: 'Close', 5: 'Volume'}
df_candle = df_candle[[0, 1, 2, 3, 4, 5]].rename(columns=rename_columns)

# 데이터가 없어 NULL 인 경우, 해당 인덱스 제거하도록 처리
df_candle = df_candle.dropna(axis=0)

# 특정 컬럼의 값을 apply 함수를 통해 모두 변경 가능하다. apply(fn) => 특정 컬럼의 값에 모두 fn 함수를 적용하여 반환
df_candle['Time'] = df_candle['Time'].apply(get_date)

df_candle.to_csv("./binance_bot/data/BTCUSDT.csv", index = False)
