import requests
import json
import os

# Data folder paths
DATA_DIR = "data"
CONFIG_DIR = os.path.join(DATA_DIR, "config")
USERS_DIR = os.path.join(DATA_DIR, "users")
USERS_CONFIG_PATH = os.path.join(CONFIG_DIR, "users_config.json")

def ensure_data_directories():
    """Ensure all necessary data directories exist"""
    for directory in [DATA_DIR, CONFIG_DIR, USERS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

def login(email, password, user_name=None, return_sid_only=False):
    """
    Login function that supports multiple users
    
    Args:
        email: User email
        password: User password
        user_name: Optional name to identify the user (for file naming)
        return_sid_only: If True, returns only session ID, otherwise returns full data
    
    Returns:
        Session ID (if return_sid_only=True) or full user data dict or None if failed
    """
    # Ensure data directories exist
    ensure_data_directories()
    
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
            print(f"Login failed for {email}: Incorrect credentials")
            return None
            
        user_data = {
            'sid': response.cookies.get('connect.sid'),
            'data': data,
            'email': email,
            'user_name': user_name or email.split('@')[0]
        }
        
        if return_sid_only:
            return user_data['sid']
            
        # Save user-specific data file in users directory
        filename = os.path.join(USERS_DIR, f"user_data_{user_data['user_name']}.json")
        with open(filename, 'w') as f:
            json.dump(user_data, f)
            
        return user_data
    else:
        print(f"Failed to login for {email}: {response.status_code}")
        return None

def load_users_config():
    """Load users configuration from data/config/users_config.json"""
    ensure_data_directories()
    
    try:
        with open(USERS_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return [user for user in config['users'] if user.get('enabled', True)]
    except FileNotFoundError:
        print(f"{USERS_CONFIG_PATH} not found. Please create it with user credentials.")
        return []
    except Exception as e:
        print(f"Error loading users config: {e}")
        return []

def login_all_users():
    """Login all enabled users and return their data"""
    users = load_users_config()
    user_sessions = {}
    
    for user in users:
        print(f"Logging in user: {user['name']} ({user['email']})")
        user_data = login(user['email'], user['password'], user['name'])
        
        if user_data:
            user_sessions[user['name']] = user_data
            print(f"✅ Login successful for {user['name']}")
        else:
            print(f"❌ Login failed for {user['name']}")
    
    return user_sessions
    
#Example usage:
# print(login("S69CSEU0001@bennett.edu.in", "camu69*"))
