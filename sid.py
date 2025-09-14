import requests
import json
import os
import hashlib
from datetime import datetime

def get_user_filename(email):
    """
    Generate a unique filename for each user based on their email
    """
    # Create a hash of the email for a clean filename
    email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
    # Extract username part before @ for readability
    username = email.split('@')[0]
    return f"user_data_{username}_{email_hash}.json"

def validate_token(sid, progression_data):
    """
    Validates if the current token is still valid by making a test API call
    """
    try:
        api_url = "https://student.bennetterp.camu.in/api/Timetable/get"
        cookies = {
            "connect.sid": sid
        }
        
        now = datetime.now()
        test_payload = progression_data.copy()
        test_payload.update({
            "enableV2": True,
            "start": now.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "usrTime": now.strftime("%d-%m-%Y, %I:%M %p"),
            "schdlTyp": "slctdSchdl",
            "isShowCancelledPeriod": True,
            "isFromTt": True
        })
        
        response = requests.post(api_url, cookies=cookies, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Check if the response indicates a valid session
            if data.get("output") and not data.get("output", {}).get("error"):
                return True
        return False
    except Exception as e:
        print(f"[DEBUG] Token validation failed: {e}")
        return False

def load_user_session(email):
    """
    Loads existing session data for a specific user if it exists and is valid
    """
    try:
        user_file = get_user_filename(email)
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                data = json.load(f)
                sid = data.get('sid')
                progression_data = data.get('data', {}).get('progressionData', [{}])[0]
                
                if sid and progression_data:
                    if validate_token(sid, progression_data):
                        print(f"[INFO] Valid session found for {email}, reusing existing token.")
                        return data
                    else:
                        print(f"[INFO] Existing token for {email} is invalid, will login again.")
                        return None
                else:
                    print(f"[INFO] Incomplete session data found for {email}.")
                    return None
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load existing session for {email}: {e}")
        return None

def save_user_session(email, session_data):
    """
    Saves session data for a specific user
    """
    try:
        user_file = get_user_filename(email)
        with open(user_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"[INFO] Session data saved for {email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save session data for {email}: {e}")
        return False

def get_user_session_data(email):
    """
    Returns the current session data for a specific user
    """
    try:
        user_file = get_user_filename(email)
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load session data for {email}: {e}")
        return None

def login(email, password, flag=True) -> bool:
    """
    Enhanced login function that handles multiple users and checks for existing valid tokens
    """
    # First, try to use existing valid session for this user
    existing_session = load_user_session(email)
    if existing_session:
        if not flag:
            return existing_session['sid']
        # Also save/update the legacy user_data.json for backward compatibility
        with open('user_data.json', 'w') as f:
            json.dump(existing_session, f)
        return True
    
    # If no valid session exists, perform login
    print(f"[INFO] Logging in {email} with credentials...")
    login_url = "https://student.bennetterp.camu.in/login/validate"
    payload = {
        "dtype": "M",
        "Email": email,
        "pwd": password
    }

    s = requests.Session()
    response = s.post(login_url, json=payload, timeout=10)
    
    if response.status_code == 200:
        data = response.json().get("output").get('data')
        if data.get('code') == 'INCRT_CRD':
            print(f"[ERROR] Login failed for {email}: Incorrect credentials.")
            return None
        
        session_data = {
            'sid': response.cookies.get('connect.sid'),
            'data': data,
            'email': email,
            'last_login': datetime.now().isoformat()
        }
        
        if not flag:
            return session_data['sid']
            
        # Save the new session data for this user
        save_user_session(email, session_data)
        
        # Also save to legacy user_data.json for backward compatibility
        with open('user_data.json', 'w') as f:
            json.dump(session_data, f)
            
        print(f"[INFO] Login successful for {email}! Session data saved.")
        return True
    else:
        print(f"[ERROR] Failed to login {email}: {response.status_code}")
        return None

def list_user_sessions():
    """
    Lists all saved user sessions
    """
    user_files = [f for f in os.listdir('.') if f.startswith('user_data_') and f.endswith('.json')]
    sessions = []
    
    for user_file in user_files:
        try:
            with open(user_file, 'r') as f:
                data = json.load(f)
                email = data.get('email', 'Unknown')
                last_login = data.get('last_login', 'Unknown')
                name = data.get('data', {}).get('logindetails', {}).get('Name', 'Unknown')
                sessions.append({
                    'email': email,
                    'name': name,
                    'last_login': last_login,
                    'file': user_file
                })
        except Exception as e:
            print(f"[ERROR] Failed to read {user_file}: {e}")
    
    return sessions
    
#Example usage:
# print(login("S69CSEU0001@bennett.edu.in", "camu69*"))
