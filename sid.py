import requests
import json
import os
import hashlib
from datetime import datetime

def log_message(level, user_email, message):
    """
    Centralized logging function with consistent formatting
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_display = user_email.split('@')[0] if user_email else "SYSTEM"
    print(f"[{timestamp}] [{level}] [{user_display}] {message}")

def ensure_data_folder():
    """
    Ensure the data folder exists, create it if it doesn't
    """
    data_folder = "data"
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        log_message("INFO", None, f"Created data folder: {data_folder}")
    return data_folder

def get_user_filename(email):
    """
    Generate a unique filename for each user based on their email
    """
    # Ensure data folder exists
    data_folder = ensure_data_folder()
    # Create a hash of the email for a clean filename
    email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
    # Extract username part before @ for readability
    username = email.split('@')[0]
    return os.path.join(data_folder, f"user_data_{username}_{email_hash}.json")

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
        log_message("ERROR", None, f"Token validation failed: {e}")
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
        log_message("INFO", email, f"Session data saved to {os.path.basename(user_file)}")
        return True
    except Exception as e:
        log_message("ERROR", email, f"Failed to save session data: {e}")
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
        log_message("ERROR", email, f"Failed to load session data: {e}")
        return None

def get_user_data_by_email(email):
    """
    Get user data (sid, json_payload, student_id) for a specific email
    Returns a dictionary with the required data or None if not found
    """
    try:
        session_data = get_user_session_data(email)
        if session_data:
            return {
                'sid': session_data['sid'],
                'json_payload': session_data['data']['progressionData'][0],
                'student_id': session_data['data']['logindetails']['Student'][0]['StuID'],
                'email': session_data.get('email', email),
                'name': session_data.get('data', {}).get('logindetails', {}).get('Name', 'Unknown')
            }
        return None
    except Exception as e:
        log_message("ERROR", email, f"Failed to extract user data: {e}")
        return None

def log_user_timetable(email):
    """
    Fetch and log the current user's timetable
    """
    try:
        from timetable import fetch_timetable_headerless
        user_data = get_user_data_by_email(email)
        if not user_data:
            log_message("ERROR", email, "Cannot fetch timetable - user data not found")
            return False
            
        log_message("INFO", email, "Fetching current timetable...")
        response = fetch_timetable_headerless(user_data['sid'], user_data['json_payload'])
        
        if response and response.get("output") and response["output"].get("data"):
            periods = response["output"]["data"][0].get("Periods", [])
            if periods:
                log_message("INFO", email, f"Today's timetable ({len(periods)} periods):")
                for i, period in enumerate(periods, 1):
                    # Extract subject name from SubNa field
                    subject_full = period.get("SubNa", "Unknown Subject")
                    # Extract just the subject name (before the first parenthesis)
                    subject = subject_full.split(" (")[0] if " (" in subject_full else subject_full
                    
                    # Extract time from FrTime and calculate end time
                    start_time = period.get("FrTime", "Unknown")
                    location = period.get("Location", "TBA")
                    faculty = period.get("StaffNm", "TBA")
                    
                    # Calculate end time (assuming 1-hour periods)
                    end_time = "Unknown"
                    if start_time != "Unknown":
                        try:
                            from datetime import datetime, timedelta
                            start_dt = datetime.strptime(start_time, "%H:%M")
                            end_dt = start_dt + timedelta(hours=1)
                            end_time = end_dt.strftime("%H:%M")
                        except:
                            end_time = "Unknown"
                    
                    time_slot = f"{start_time}-{end_time}"
                    log_message("INFO", email, f"  {i}. {subject} | {time_slot} | Room: {location} | Faculty: {faculty}")
            else:
                log_message("INFO", email, "No classes scheduled for today")
        else:
            log_message("WARN", email, "Could not retrieve timetable data")
        return True
    except Exception as e:
        log_message("ERROR", email, f"Failed to fetch timetable: {e}")
        return False

def login(email, password, flag=True) -> bool:
    """
    Enhanced login function that handles multiple users and checks for existing valid tokens
    """
    log_message("INFO", email, "Starting authentication process...")
    
    # First, try to use existing valid session for this user
    existing_session = load_user_session(email)
    if existing_session:
        log_message("INFO", email, "Found existing session, validating...")
        if validate_token(existing_session['sid'], existing_session['data']['progressionData'][0]):
            log_message("SUCCESS", email, "Existing session is still valid!")
            # Log timetable for returning user
            log_user_timetable(email)
            if not flag:
                return existing_session['sid']
            return True
        else:
            log_message("WARN", email, "Existing session expired, performing fresh login...")
    
    # If no valid session exists, perform login
    log_message("INFO", email, "Performing credential-based login...")
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
            log_message("ERROR", email, "Login failed - Incorrect credentials")
            return None
        
        # Extract user info for logging
        user_name = data.get('logindetails', {}).get('Name', 'Unknown')
        student_id = data.get('logindetails', {}).get('Student', [{}])[0].get('StuID', 'Unknown')
        
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
        
        log_message("SUCCESS", email, f"Login successful! Welcome {user_name} (ID: {student_id})")
        
        # Log timetable for newly logged in user
        log_user_timetable(email)
        
        return True
    else:
        log_message("ERROR", email, f"Login failed - Server error: {response.status_code}")
        return None

def list_user_sessions():
    """
    Lists all saved user sessions
    """
    data_folder = ensure_data_folder()
    user_files = [f for f in os.listdir(data_folder) if f.startswith('user_data_') and f.endswith('.json')]
    sessions = []
    
    for user_file in user_files:
        try:
            with open(os.path.join(data_folder, user_file), 'r') as f:
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
