import requests
import json
import logging
import os

def login(email,password,flag=True)-> bool:
    logger = logging.getLogger('attendance_main')
    login_url = "https://student.bennetterp.camu.in/login/validate"
    payload = {
        "dtype": "M",
        "Email": email,
        "pwd": password
    }

    s = requests.Session()
    try:
        response = s.post(login_url, json=payload,timeout=10)
        
        if response.status_code == 200:
            data =response.json().get("output").get('data')
            if data.get('code')=='INCRT_CRD':
                logger.error(f"Login failed: Incorrect credentials for {email}")
                return None
            data = {
                'sid':response.cookies.get('connect.sid'),
                'data' : data
            }
            if not flag:
                logger.debug(f"Session refreshed for {email}")
                return data['sid']
            
            # Create sessions directory if it doesn't exist
            if not os.path.exists('sessions'):
                os.makedirs('sessions')
                logger.debug("Created sessions directory")
            
            with open('sessions/user_data.json', 'w') as f:
                json.dump(data,f)
            logger.debug(f"Login successful and data saved to sessions/user_data.json for {email}")
            return True
        else:
            logger.error(f"Failed to login: HTTP {response.status_code} for {email}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Login request timed out for {email}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during login for {email}: {e}")
        return None
    
#Example usage:
# print(login("S69CSEU0001@bennett.edu.in", "camu69*"))
