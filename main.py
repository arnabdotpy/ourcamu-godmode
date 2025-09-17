import asyncio
import threading
import json
import time
from timetable import *
from markit import *
from sid import *

USERS = [
    {
        "email": "e23cseu0688@bennett.edu.in",
        "password": "Arka@671",
        "name": "Arkade"
    },
    {
        "email": "e23cseu0705@bennett.edu.in", 
        "password": "Reo@#2004",
        "name": "Arnab"
    },
    {
        "email": "e23cseu0679@bennett.edu.in",
        "password": "U0b6K0ED",
        "name": "Abhshek"
    },
    {
        "email": "e23cseu0672@bennett.edu.in",
        "password": "10-11-2005",
        "name": "Piyush"
    },
    {
        "email": "e23cseu0036@bennett.edu.in",
        "password": "8lHTcGVA",
        "name": "Grisha"
    },
]
if not USERS:
    print("No users configured.")
    exit(1)

# Store user data for each user
user_sessions = {}

def initialize_user_session(user):
    """Initialize session data for a user"""
    email = user["email"]
    password = user["password"]
    name = user["name"]
    
    print(f"Initializing session for {name} ({email})...")
    
    # Login and create user-specific data file
    login_result = login(email, password)
    if login_result:
        print(f"Login successful for {name}!")
        
        # Create user-specific filename
        user_filename = f"user_data_{name.lower()}.json"
        
        # Read the general user_data.json that was created by login
        with open('user_data.json','r') as f:
            data = json.load(f)
            sid = data['sid']
            json_payload = data['data']['progressionData'][0]
            stuId = data['data']['logindetails']['Student'][0]['StuID']
        
        # Save user-specific data
        with open(user_filename, 'w') as f:
            json.dump(data, f)
            
        user_sessions[email] = {
            'name': name,
            'email': email,
            'password': password,
            'sid': sid,
            'json_payload': json_payload,
            'stuId': stuId,
            'data_file': user_filename
        }
        return True
    else:
        print(f"Login failed for {name}. Please check email and password.")
        return False


async def extract_pending_attendance_classes(sid, json_payload):
    result = {}
    response = fetch_timetable_headerless(sid, json_payload)
    #print(type(response))
    try:
        # print(response)
        periods = response["output"]["data"][0]["Periods"]
        # print(periods)
        for cls in periods:
            if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
    except Exception as e:
        print(f"[ERROR] while extracting periods: {e}")
    # print(result)
    return result

async def user_attendance_loop(user_session):
    """Handle attendance marking for a single user"""
    name = user_session['name']
    email = user_session['email']
    password = user_session['password']
    
    while True:
        try:
            # Refresh session ID
            sid = login(email, password, flag=False)
            if not sid:
                print(f"[ERROR] Failed to refresh session for {name}")
                await asyncio.sleep(30)
                continue
                
            user_session['sid'] = sid
            
            pending = await extract_pending_attendance_classes(sid, user_session['json_payload'])
            #print(type(pending))
            # print('GO')
            print(f"Starting to mark attendance for {name}... [{sid}]")
            tasks = []
            for i in pending.values():
                print(f"{name}: {i[0]}")
                tasks.append(asyncio.create_task(mark_attendance(sid, i[0], user_session['stuId'])))
            if tasks:
                await asyncio.gather(*tasks)
                print(f"Attendance marked successfully for {name}.")
                print("\n")
            await asyncio.sleep(1)
        except TimeoutError:
            print(f"[ERROR] Request timed out for {name}. Please check your internet connection.")
            continue
        except Exception as e:
            print(f"[ERROR] While fetching attendance for {name}: {e}")
            continue
def run_user_attendance(user_session):
    """Run attendance loop for a user in a thread"""
    try:
        asyncio.run(user_attendance_loop(user_session))
    except KeyboardInterrupt:
        print(f"\nStopping attendance for {user_session['name']}...")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred for {user_session['name']}: {e}")

def main():
    """Main function to initialize and run attendance for all users"""
    print("Initializing sessions for all users...")
    
    # Initialize sessions for all users
    successful_users = []
    for user in USERS:
        if initialize_user_session(user):
            successful_users.append(user["email"])
    
    if not successful_users:
        print("No users could log in successfully. Exiting.")
        exit(1)
    
    print(f"\nSuccessfully initialized {len(successful_users)} users.")
    print("Starting attendance threads for all users...")
    
    # Create and start threads for each user
    threads = []
    for email in successful_users:
        user_session = user_sessions[email]
        thread = threading.Thread(
            target=run_user_attendance, 
            args=(user_session,),
            daemon=True,
            name=f"AttendanceThread-{user_session['name']}"
        )
        threads.append(thread)
        thread.start()
        print(f"Started attendance thread for {user_session['name']}")
    
    print(f"\nAll {len(threads)} threads started successfully!")
    print("Press Ctrl+C to stop all threads...\n")
    
    try:
        # Keep main thread alive and wait for all threads
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal. Stopping all threads...")
        print("Please wait for all threads to finish...")
        # Threads are daemon threads, so they will stop when main thread exits

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping the Script now...")
        exit(0)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        exit(1)
