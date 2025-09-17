import requests
import json

def login(email,password,flag=True)-> bool:
    login_url = "https://student.bennetterp.camu.in/login/validate"
    payload = {
        "dtype": "M",
        "Email": email,
        "pwd": password
    }

    s = requests.Session()
    response = s.post(login_url, json=payload,timeout=10)
    
    if response.status_code == 200:
        data =response.json().get("output").get('data')
        if data.get('code')=='INCRT_CRD':
            # print("Login failed: No data returned.")
            return None
        data = {
            'sid':response.cookies.get('connect.sid'),
            'data' : data
        }
        if not flag:
            return data['sid']
        with open('user_data.json', 'w') as f:
            json.dump(data,f)
        return True
    else:
        print(f"Failed to login: {response.status_code}")
        return None
    
#Example usage:
# print(login("S69CSEU0001@bennett.edu.in", "camu69*"))
