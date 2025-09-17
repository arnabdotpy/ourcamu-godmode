import requests
import logging
from datetime import datetime

from sid import *

def fetch_timetable_headerless(sid, json_payload):
    logger = logging.getLogger('attendance_main')
    api_url = "https://student.bennetterp.camu.in/api/Timetable/get"
    cookies = {
        "connect.sid": sid
    }

    now=datetime.now()

    json_payload.update({
        "enableV2": True,
        "start": now.strftime("%Y-%m-%d"),
        "end": now.strftime("%Y-%m-%d"),
        "usrTime": now.strftime("%d-%m-%Y, %I:%M %p"),
        "schdlTyp": "slctdSchdl",
        "isShowCancelledPeriod": True,
        "isFromTt": True
    })
    
    try:
        logger.debug(f"Fetching timetable for date: {now.strftime('%Y-%m-%d')}")
        response = requests.post(api_url, cookies=cookies, json=json_payload,timeout=5)

        # Check if the response status code indicates success
        if response.status_code == 200:
            logger.debug("Timetable fetched successfully")
            return response.json()
        else:
            logger.error(f"Error: Received status code {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

# with open('user_data.json','r') as f:
#     data = json.load(f)
#     sid = data['sid']
#     json_payload = data['data']['progressionData'][0]

#     print(fetch_timetable_headerless(sid,json_payload))
