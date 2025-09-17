import asyncio
import threading
import json
import time
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
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
        "name": "Abhishek"
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

def setup_logging():
    """Setup comprehensive logging system"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Setup main logger
    main_logger = logging.getLogger('attendance_main')
    main_logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    main_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler for main logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    main_logger.addHandler(console_handler)
    
    # File handler for main logs with rotation
    main_file_handler = RotatingFileHandler(
        'logs/attendance_main.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    main_file_handler.setLevel(logging.DEBUG)
    main_file_handler.setFormatter(detailed_formatter)
    main_logger.addHandler(main_file_handler)
    
    return main_logger

def setup_user_logger(name):
    """Setup logger for individual user"""
    logger_name = f'user_{name.lower()}'
    user_logger = logging.getLogger(logger_name)
    user_logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    user_logger.handlers.clear()
    
    # Prevent propagation to avoid duplicate logs
    user_logger.propagate = False
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for user-specific logs
    user_file_handler = RotatingFileHandler(
        f'logs/attendance_{name.lower()}.log',
        maxBytes=2*1024*1024,  # 2MB
        backupCount=2
    )
    user_file_handler.setLevel(logging.DEBUG)
    user_file_handler.setFormatter(detailed_formatter)
    user_logger.addHandler(user_file_handler)
    
    # Console handler for user (only warnings and errors to avoid spam)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(f'[{name}] %(levelname)s - %(message)s'))
    user_logger.addHandler(console_handler)
    
    return user_logger

# Initialize main logger
main_logger = setup_logging()
if not USERS:
    main_logger.error("No users configured.")
    exit(1)

# Store user data for each user
user_sessions = {}

def initialize_user_session(user):
    """Initialize session data for a user"""
    email = user["email"]
    password = user["password"]
    name = user["name"]
    
    main_logger.info(f"Initializing session for {name} ({email})...")
    
    # Create sessions directory if it doesn't exist
    if not os.path.exists('sessions'):
        os.makedirs('sessions')
        main_logger.debug("Created sessions directory")
    
    # Login and create user-specific data file
    login_result = login(email, password)
    if login_result:
        main_logger.info(f"Login successful for {name}!")
        
        # Create user-specific filename in sessions folder
        user_filename = f"sessions/user_data_{name.lower()}.json"
        
        # Read the general user_data.json that was created by login
        with open('sessions/user_data.json','r') as f:
            data = json.load(f)
            sid = data['sid']
            json_payload = data['data']['progressionData'][0]
            stuId = data['data']['logindetails']['Student'][0]['StuID']
        
        # Save user-specific data
        with open(user_filename, 'w') as f:
            json.dump(data, f)
        
        # Setup user-specific logger
        user_logger = setup_user_logger(name)
        user_logger.info(f"Session initialized successfully for {name}")
        user_logger.debug(f"Session ID: {sid[:10]}...")
        user_logger.debug(f"Student ID: {stuId}")
        user_logger.debug(f"Session data saved to: {user_filename}")
            
        user_sessions[email] = {
            'name': name,
            'email': email,
            'password': password,
            'sid': sid,
            'json_payload': json_payload,
            'stuId': stuId,
            'data_file': user_filename,
            'logger': user_logger
        }
        return True
    else:
        main_logger.error(f"Login failed for {name}. Please check email and password.")
        return False


async def extract_pending_attendance_classes(sid, json_payload, user_logger):
    result = {}
    user_logger.debug("Fetching timetable data...")
    response = fetch_timetable_headerless(sid, json_payload)
    
    try:
        periods = response["output"]["data"][0]["Periods"]
        user_logger.debug(f"Found {len(periods)} periods in timetable")
        
        for cls in periods:
            if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
                user_logger.debug(f"Found pending attendance: Period {cls['PeriodId']}, Attendance ID: {cls['attendanceId']}")
        
        user_logger.info(f"Found {len(result)} pending attendance classes")
        
    except Exception as e:
        user_logger.error(f"Error while extracting periods: {e}")
    
    return result

async def user_attendance_loop(user_session):
    """Handle attendance marking for a single user"""
    name = user_session['name']
    email = user_session['email']
    password = user_session['password']
    user_logger = user_session['logger']
    
    user_logger.info(f"Starting attendance monitoring loop for {name}")
    
    # Use the initial session ID from login
    sid = user_session['sid']
    session_refresh_count = 0
    last_session_check = time.time()
    session_check_interval = 300  # Check session validity every 5 minutes
    
    while True:
        try:
            # Periodic session validation (every 5 minutes)
            current_time = time.time()
            if current_time - last_session_check > session_check_interval:
                user_logger.debug("Performing periodic session validation...")
                if not validate_session(sid):
                    user_logger.warning("Session validation failed, refreshing session...")
                    new_sid = login(email, password, flag=False)
                    if new_sid:
                        sid = new_sid
                        user_session['sid'] = sid
                        session_refresh_count += 1
                        user_logger.info(f"Session refreshed successfully (refresh #{session_refresh_count}): {sid[:10]}...")
                    else:
                        user_logger.error("Failed to refresh session during validation, retrying in 30 seconds...")
                        await asyncio.sleep(30)
                        continue
                else:
                    user_logger.debug("Session validation passed")
                last_session_check = current_time
            
            # Use existing session ID - no need to login every time
            user_logger.debug(f"Using existing session: {sid[:10]}...")
            
            pending = await extract_pending_attendance_classes(sid, user_session['json_payload'], user_logger)
            
            if pending:
                user_logger.info(f"Starting to mark attendance for {len(pending)} classes...")
                tasks = []
                for period_id, (attendance_id, _) in pending.items():
                    user_logger.debug(f"Creating task for attendance ID: {attendance_id}")
                    tasks.append(asyncio.create_task(mark_attendance(sid, attendance_id, user_session['stuId'])))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Log results
                    success_count = 0
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            user_logger.error(f"Task {i+1} failed: {result}")
                        else:
                            if result:
                                success_count += 1
                            user_logger.debug(f"Task {i+1} result: {result}")
                    
                    user_logger.info(f"Attendance marking completed: {success_count}/{len(tasks)} successful")
            else:
                user_logger.debug("No pending attendance found")
                
            await asyncio.sleep(1)
            
        except Exception as e:
            # Check if the error might be session-related
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['session', 'unauthorized', 'forbidden', 'authentication', 'invalid', '401', '403']):
                user_logger.warning(f"Session-related error detected: {e}")
                user_logger.info("Attempting to refresh session...")
                
                # Refresh session only when needed
                new_sid = login(email, password, flag=False)
                if new_sid:
                    sid = new_sid
                    user_session['sid'] = sid
                    session_refresh_count += 1
                    user_logger.info(f"Session refreshed successfully (refresh #{session_refresh_count}): {sid[:10]}...")
                    last_session_check = time.time()  # Reset check timer after refresh
                else:
                    user_logger.error("Failed to refresh session, retrying in 30 seconds...")
                    await asyncio.sleep(30)
                    continue
            else:
                user_logger.error(f"Unexpected error while fetching attendance: {e}")
                await asyncio.sleep(5)
            continue
def run_user_attendance(user_session):
    """Run attendance loop for a user in a thread"""
    name = user_session['name']
    user_logger = user_session['logger']
    
    try:
        user_logger.info("Thread started successfully")
        asyncio.run(user_attendance_loop(user_session))
    except KeyboardInterrupt:
        user_logger.info("Received interrupt signal, stopping attendance monitoring")
    except Exception as e:
        user_logger.error(f"Unexpected error in attendance thread: {e}")

def main():
    """Main function to initialize and run attendance for all users"""
    main_logger.info("=== OURCAMU Attendance Bot Started ===")
    main_logger.info(f"Configured users: {len(USERS)}")
    
    # Initialize sessions for all users
    successful_users = []
    for user in USERS:
        if initialize_user_session(user):
            successful_users.append(user["email"])
    
    if not successful_users:
        main_logger.error("No users could log in successfully. Exiting.")
        exit(1)
    
    main_logger.info(f"Successfully initialized {len(successful_users)}/{len(USERS)} users")
    main_logger.info("Starting attendance threads for all users...")
    
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
        main_logger.info(f"Started attendance thread for {user_session['name']}")
    
    main_logger.info(f"All {len(threads)} threads started successfully!")
    main_logger.info("Press Ctrl+C to stop all threads...")
    
    try:
        # Keep main thread alive and wait for all threads
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        main_logger.info("Received interrupt signal. Stopping all threads...")
        main_logger.info("Please wait for all threads to finish...")
        # Threads are daemon threads, so they will stop when main thread exits

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        main_logger.info("Application terminated by user")
        exit(0)
    except Exception as e:
        main_logger.error(f"Fatal error occurred: {e}")
        exit(1)
    finally:
        main_logger.info("=== OURCAMU Attendance Bot Stopped ===")
        # Ensure all logs are flushed
        for handler in main_logger.handlers:
            handler.flush()
