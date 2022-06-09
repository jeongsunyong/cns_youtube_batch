import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.background import BlockingScheduler

scheduler=BlockingScheduler(timezone='Asia/Seoul')

#@scheduler.scheduled_job(cron,hour='12',minuite'00',id='ytb_col')
@scheduler.scheduled_job('interval',seconds=60,id='ytb_col_test')
def job():
    os.system(f"echo {time.strftime('%H:%M:%S')}")
    print(f" scheduler test {time.strftime('%H:%M:%S')}")

if __name__=="__main__":
    #scheduler=BackgroundScheduler()
    #scheduler=BlockingScheduler(timezone='Asia/Seoul')
    scheduler.start()
