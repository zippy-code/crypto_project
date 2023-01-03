from apscheduler.schedulers.background import BlockingScheduler
import requests
import crypto_bot_auth as cauth

def bitAlert():

    global scheduler

    result = requests.get("https://api.cryptoquant.com/v1/btc/exchange-flows/inflow?exchange=all_exchange&window=block&limit=5",
        headers = {
            'Authorization': cauth.Authorization_cryptoquant
        }).json()

    if (result['result']['data'][0]["inflow_mean"] > 5):
        requests.post("https://slack.com/api/chat.postMessage",
            headers = { "Authorization": "Bearer xoxb-4595599626609-4580262216405-vMKc57gldJK2GiWmSCplchax" },
            data= {
                "channel": "#checkbot",
                "text": str(result['result']['data'][0]["inflow_mean"]) +"개 비트코인 -> 거래소 이동 포착! "
                }
            )

scheduler = BlockingScheduler()
scheduler.add_job(bitAlert, 'interval', seconds = 5, id = 'example', args = [])

scheduler.start()