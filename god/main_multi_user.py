import asyncio
import json
import os
from datetime import datetime
from timetable import *
from markit import *
from sid import *

def log(level, message, user=None):
    """Professional logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f" [{user}]" if user else ""
    print(f"[{timestamp}]{user_info} {level}: {message}")

def log_to_file(message, user=None):
    """Log successful attendance markings to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure logs directory exists
    log_dir = os.path.join("data", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create log filename with date
    log_filename = os.path.join(log_dir, f"attendance_success_{date_str}.log")
    
    user_info = f" [{user}]" if user else ""
    log_entry = f"[{timestamp}]{user_info} {message}\n"
    
    try:
        with open(log_filename, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        log("ERROR", f"Failed to write to log file: {e}")

class MultiUserAttendanceBot:
    def __init__(self):
        self.user_sessions = {}
        self.running_tasks = {}
        # Ensure data directories exist
        ensure_data_directories()
    
    async def extract_pending_attendance_classes(self, user_data):
        """Extract pending attendance classes for a specific user"""
        result = {}
        try:
            sid = user_data['sid']
            json_payload = user_data['data']['progressionData'][0]
            
            response = fetch_timetable_headerless(sid, json_payload)
            if not response:
                return result
                
            periods = response["output"]["data"][0]["Periods"]
            for cls in periods:
                if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                    result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
        except Exception as e:
            log("ERROR", f"Failed to extract pending attendance classes: {e}", user_data.get('user_name', 'unknown'))
        
        return result
    
    async def refresh_user_session(self, user_name, user_data):
        """Refresh session for a single user"""
        try:
            # Get password from config
            users_config = load_users_config()
            password = None
            for user in users_config:
                if user['name'] == user_name:
                    password = user['password']
                    break
            
            if not password:
                log("ERROR", "Password not found in configuration", user_name)
                return False
            
            # Get fresh session ID
            email = user_data['email']
            sid = login(email, password, user_name, return_sid_only=True)
            if not sid:
                log("WARNING", "Session refresh failed - login unsuccessful", user_name)
                return False
            
            # Update session in user data
            user_data['sid'] = sid
            return True
            
        except Exception as e:
            log("ERROR", f"Session refresh failed: {e}", user_name)
            return False
    
    async def process_all_users_cycle(self):
        """Process attendance for all users in a single cycle"""
        log("INFO", f"Starting attendance cycle for {len(self.user_sessions)} users")
        
        # Step 1: Refresh sessions for all users concurrently
        log("INFO", "Refreshing authentication sessions for all users")
        refresh_tasks = []
        for user_name, user_data in self.user_sessions.items():
            task = asyncio.create_task(self.refresh_user_session(user_name, user_data))
            refresh_tasks.append((user_name, task))
        
        # Wait for all session refreshes to complete
        refresh_results = await asyncio.gather(*[task for _, task in refresh_tasks])
        
        # Check which users successfully refreshed
        active_users = []
        for i, (user_name, _) in enumerate(refresh_tasks):
            if refresh_results[i]:
                active_users.append(user_name)
                log("SUCCESS", "Session authenticated successfully", user_name)
            else:
                log("WARNING", "Session authentication failed", user_name)
        
        if not active_users:
            log("WARNING", "No users have valid sessions - skipping attendance cycle")
            return
        
        # Step 2: Extract pending classes for all active users concurrently
        log("INFO", "Checking for pending attendance records")
        pending_tasks = []
        for user_name in active_users:
            user_data = self.user_sessions[user_name]
            task = asyncio.create_task(self.extract_pending_attendance_classes(user_data))
            pending_tasks.append((user_name, task))
        
        # Wait for all pending class extractions to complete
        pending_results = await asyncio.gather(*[task for _, task in pending_tasks])
        
        # Step 3: Collect all attendance tasks for all users
        all_attendance_tasks = []
        total_pending = 0
        
        for i, (user_name, _) in enumerate(pending_tasks):
            pending = pending_results[i]
            user_data = self.user_sessions[user_name]
            
            if pending:
                log("INFO", f"Found {len(pending)} pending attendance records", user_name)
                total_pending += len(pending)
                
                # Get student ID and session
                stuId = user_data['data']['logindetails']['Student'][0]['StuID']
                sid = user_data['sid']
                
                # Create attendance tasks for this user
                for attendance_info in pending.values():
                    attendance_id = attendance_info[0]
                    task = asyncio.create_task(mark_attendance(sid, attendance_id, stuId))
                    all_attendance_tasks.append((user_name, task))
            else:
                log("INFO", "No pending attendance records found", user_name)
        
        # Step 4: Execute all attendance marking concurrently
        if all_attendance_tasks:
            log("INFO", f"Processing {total_pending} attendance records concurrently across all users")
            
            # Execute all attendance tasks at once
            attendance_results = await asyncio.gather(*[task for _, task in all_attendance_tasks])
            
            # Count successes per user
            user_success_count = {}
            for i, (user_name, _) in enumerate(all_attendance_tasks):
                if user_name not in user_success_count:
                    user_success_count[user_name] = 0
                if attendance_results[i]:
                    user_success_count[user_name] += 1
            
            # Report results and log to file
            for user_name in active_users:
                success_count = user_success_count.get(user_name, 0)
                if success_count > 0:
                    success_message = f"Successfully marked {success_count} attendance records"
                    log("SUCCESS", success_message, user_name)
                    # Log to file for successful attendance
                    log_to_file(f"SUCCESS: {success_message}", user_name)
        else:
            log("INFO", "No attendance records to process for any user")
        
        log("SUCCESS", "Attendance cycle completed for all users")
        
        # Log cycle completion to file if any attendance was marked
        if all_attendance_tasks:
            total_success = sum(user_success_count.values())
            cycle_summary = f"Cycle completed - Total records processed: {total_success}/{total_pending}"
            log_to_file(f"CYCLE_COMPLETE: {cycle_summary}")
        
        print()  # Empty line for readability

    async def start_all_users(self):
        """Start attendance processing for all users together"""
        # Login all users
        log("INFO", "Starting Multi-User Attendance Bot")
        self.user_sessions = login_all_users()
        
        if not self.user_sessions:
            log("ERROR", "No users logged in successfully - terminating application")
            return
        
        log("SUCCESS", f"Successfully authenticated {len(self.user_sessions)} users")
        log("INFO", "Starting unified attendance processing cycle")
        print()  # Empty line for readability
        
        # Run unified processing cycle
        try:
            while True:
                await self.process_all_users_cycle()
                
                # Wait before next cycle
                log("DEBUG", "Waiting 1 second before next cycle")
                await asyncio.sleep(1)
                
        except Exception as e:
            log("ERROR", f"Critical error in attendance processing: {e}")
    
    def stop_all_users(self):
        """Stop all running user tasks"""
        log("INFO", "Stopping all user tasks")
        for user_name, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                log("INFO", "Task stopped", user_name)

async def main():
    """Main function to run the multi-user attendance bot"""
    bot = MultiUserAttendanceBot()
    
    try:
        await bot.start_all_users()
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Received interrupt signal - shutting down gracefully")
        bot.stop_all_users()
    except Exception as e:
        log("ERROR", f"Unexpected error in main application: {e}")
        bot.stop_all_users()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Multi-User Attendance Bot terminated successfully")
    except Exception as e:
        log("ERROR", f"Fatal application error: {e}")

def log_to_file(message, user=None):
    """Log successful attendance markings to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure logs directory exists
    log_dir = os.path.join("data", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create log filename with date
    log_filename = os.path.join(log_dir, f"attendance_success_{date_str}.log")
    
    user_info = f" [{user}]" if user else ""
    log_entry = f"[{timestamp}]{user_info} {message}\n"
    
    try:
        with open(log_filename, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        log("ERROR", f"Failed to write to log file: {e}")

class MultiUserAttendanceBot:
    def __init__(self):
        self.user_sessions = {}
        self.running_tasks = {}
        # Ensure data directories exist
        ensure_data_directories()
    
    async def extract_pending_attendance_classes(self, user_data):
        """Extract pending attendance classes for a specific user"""
        result = {}
        try:
            sid = user_data['sid']
            json_payload = user_data['data']['progressionData'][0]
            
            response = fetch_timetable_headerless(sid, json_payload)
            if not response:
                return result
                
            periods = response["output"]["data"][0]["Periods"]
            for cls in periods:
                if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                    result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
        except Exception as e:
            log("ERROR", f"Failed to extract pending attendance classes: {e}", user_data.get('user_name', 'unknown'))
        
        return result
    
    async def refresh_user_session(self, user_name, user_data):
        """Refresh session for a single user"""
        try:
            # Get password from config
            users_config = load_users_config()
            password = None
            for user in users_config:
                if user['name'] == user_name:
                    password = user['password']
                    break
            
            if not password:
                log("ERROR", "Password not found in configuration", user_name)
                return False
            
            # Get fresh session ID
            email = user_data['email']
            sid = login(email, password, user_name, return_sid_only=True)
            if not sid:
                log("WARNING", "Session refresh failed - login unsuccessful", user_name)
                return False
            
            # Update session in user data
            user_data['sid'] = sid
            return True
            
        except Exception as e:
            log("ERROR", f"Session refresh failed: {e}", user_name)
            return False
    
    async def process_all_users_cycle(self):
        """Process attendance for all users in a single cycle"""
        log("INFO", f"Starting attendance cycle for {len(self.user_sessions)} users")
        
        # Step 1: Refresh sessions for all users concurrently
        log("INFO", "Refreshing authentication sessions for all users")
        refresh_tasks = []
        for user_name, user_data in self.user_sessions.items():
            task = asyncio.create_task(self.refresh_user_session(user_name, user_data))
            refresh_tasks.append((user_name, task))
        
        # Wait for all session refreshes to complete
        refresh_results = await asyncio.gather(*[task for _, task in refresh_tasks])
        
        # Check which users successfully refreshed
        active_users = []
        for i, (user_name, _) in enumerate(refresh_tasks):
            if refresh_results[i]:
                active_users.append(user_name)
                log("SUCCESS", "Session authenticated successfully", user_name)
            else:
                log("WARNING", "Session authentication failed", user_name)
        
        if not active_users:
            log("WARNING", "No users have valid sessions - skipping attendance cycle")
            return
        
        # Step 2: Extract pending classes for all active users concurrently
        log("INFO", "Checking for pending attendance records")
        pending_tasks = []
        for user_name in active_users:
            user_data = self.user_sessions[user_name]
            task = asyncio.create_task(self.extract_pending_attendance_classes(user_data))
            pending_tasks.append((user_name, task))
        
        # Wait for all pending class extractions to complete
        pending_results = await asyncio.gather(*[task for _, task in pending_tasks])
        
        # Step 3: Collect all attendance tasks for all users
        all_attendance_tasks = []
        total_pending = 0
        
        for i, (user_name, _) in enumerate(pending_tasks):
            pending = pending_results[i]
            user_data = self.user_sessions[user_name]
            
            if pending:
                log("INFO", f"Found {len(pending)} pending attendance records", user_name)
                total_pending += len(pending)
                
                # Get student ID and session
                stuId = user_data['data']['logindetails']['Student'][0]['StuID']
                sid = user_data['sid']
                
                # Create attendance tasks for this user
                for attendance_info in pending.values():
                    attendance_id = attendance_info[0]
                    task = asyncio.create_task(mark_attendance(sid, attendance_id, stuId))
                    all_attendance_tasks.append((user_name, task))
            else:
                log("INFO", "No pending attendance records found", user_name)
        
        # Step 4: Execute all attendance marking concurrently
        if all_attendance_tasks:
            log("INFO", f"Processing {total_pending} attendance records concurrently across all users")
            
            # Execute all attendance tasks at once
            attendance_results = await asyncio.gather(*[task for _, task in all_attendance_tasks])
            
            # Count successes per user
            user_success_count = {}
            for i, (user_name, _) in enumerate(all_attendance_tasks):
                if user_name not in user_success_count:
                    user_success_count[user_name] = 0
                if attendance_results[i]:
                    user_success_count[user_name] += 1
            
            # Report results
            for user_name in active_users:
                success_count = user_success_count.get(user_name, 0)
                if success_count > 0:
                    log("SUCCESS", f"Successfully marked {success_count} attendance records", user_name)
        else:
            log("INFO", "No attendance records to process for any user")
        
        log("SUCCESS", "Attendance cycle completed for all users")
        print()  # Empty line for readability

    async def start_all_users(self):
        """Start attendance processing for all users together"""
        # Login all users
        log("INFO", "Starting Multi-User Attendance Bot")
        self.user_sessions = login_all_users()
        
        if not self.user_sessions:
            log("ERROR", "No users logged in successfully - terminating application")
            return
        
        log("SUCCESS", f"Successfully authenticated {len(self.user_sessions)} users")
        log("INFO", "Starting unified attendance processing cycle")
        print()  # Empty line for readability
        
        # Run unified processing cycle
        try:
            while True:
                await self.process_all_users_cycle()
                
                # Wait before next cycle
                log("DEBUG", "Waiting 1 second before next cycle")
                await asyncio.sleep(1)
                
        except Exception as e:
            log("ERROR", f"Critical error in attendance processing: {e}")
    
    def stop_all_users(self):
        """Stop all running user tasks"""
        log("INFO", "Stopping all user tasks")
        for user_name, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                log("INFO", "Task stopped", user_name)

async def main():
    """Main function to run the multi-user attendance bot"""
    bot = MultiUserAttendanceBot()
    
    try:
        await bot.start_all_users()
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Received interrupt signal - shutting down gracefully")
        bot.stop_all_users()
    except Exception as e:
        log("ERROR", f"Unexpected error in main application: {e}")
        bot.stop_all_users()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Multi-User Attendance Bot terminated successfully")
    except Exception as e:
        log("ERROR", f"Fatal application error: {e}")

def log(level, message, user=None):
    """Professional logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info = f" [{user}]" if user else ""
    print(f"[{timestamp}]{user_info} {level}: {message}")

class MultiUserAttendanceBot:
    def __init__(self):
        self.user_sessions = {}
        self.running_tasks = {}
        # Ensure data directories exist
        ensure_data_directories()
    
    async def extract_pending_attendance_classes(self, user_data):
        """Extract pending attendance classes for a specific user"""
        result = {}
        try:
            sid = user_data['sid']
            json_payload = user_data['data']['progressionData'][0]
            
            response = fetch_timetable_headerless(sid, json_payload)
            if not response:
                return result
                
            periods = response["output"]["data"][0]["Periods"]
            for cls in periods:
                if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                    result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
        except Exception as e:
            log("ERROR", f"Failed to extract pending attendance classes: {e}", user_data.get('user_name', 'unknown'))
        
        return result
    
    async def refresh_user_session(self, user_name, user_data):
        """Refresh session for a single user"""
        try:
            # Get password from config
            users_config = load_users_config()
            password = None
            for user in users_config:
                if user['name'] == user_name:
                    password = user['password']
                    break
            
            if not password:
                log("ERROR", "Password not found in configuration", user_name)
                return False
            
            # Get fresh session ID
            email = user_data['email']
            sid = login(email, password, user_name, return_sid_only=True)
            if not sid:
                log("WARNING", "Session refresh failed - login unsuccessful", user_name)
                return False
            
            # Update session in user data
            user_data['sid'] = sid
            return True
            
        except Exception as e:
            log("ERROR", f"Session refresh failed: {e}", user_name)
            return False
    
    async def process_all_users_cycle(self):
        """Process attendance for all users in a single cycle"""
        log("INFO", f"Starting attendance cycle for {len(self.user_sessions)} users")
        
        # Step 1: Refresh sessions for all users concurrently
        log("INFO", "Refreshing authentication sessions for all users")
        refresh_tasks = []
        for user_name, user_data in self.user_sessions.items():
            task = asyncio.create_task(self.refresh_user_session(user_name, user_data))
            refresh_tasks.append((user_name, task))
        
        # Wait for all session refreshes to complete
        refresh_results = await asyncio.gather(*[task for _, task in refresh_tasks])
        
        # Check which users successfully refreshed
        active_users = []
        for i, (user_name, _) in enumerate(refresh_tasks):
            if refresh_results[i]:
                active_users.append(user_name)
                log("SUCCESS", "Session authenticated successfully", user_name)
            else:
                log("WARNING", "Session authentication failed", user_name)
        
        if not active_users:
            log("WARNING", "No users have valid sessions - skipping attendance cycle")
            return
        
        # Step 2: Extract pending classes for all active users concurrently
        log("INFO", "Checking for pending attendance records")
        pending_tasks = []
        for user_name in active_users:
            user_data = self.user_sessions[user_name]
            task = asyncio.create_task(self.extract_pending_attendance_classes(user_data))
            pending_tasks.append((user_name, task))
        
        # Wait for all pending class extractions to complete
        pending_results = await asyncio.gather(*[task for _, task in pending_tasks])
        
        # Step 3: Collect all attendance tasks for all users
        all_attendance_tasks = []
        total_pending = 0
        
        for i, (user_name, _) in enumerate(pending_tasks):
            pending = pending_results[i]
            user_data = self.user_sessions[user_name]
            
            if pending:
                print(f"� Found {len(pending)} pending classes for {user_name}")
                total_pending += len(pending)
                
                # Get student ID and session
                stuId = user_data['data']['logindetails']['Student'][0]['StuID']
                sid = user_data['sid']
                
                # Create attendance tasks for this user
                for attendance_info in pending.values():
                    attendance_id = attendance_info[0]
                    task = asyncio.create_task(mark_attendance(sid, attendance_id, stuId))
                    all_attendance_tasks.append((user_name, task))
            else:
                log("INFO", "No pending attendance records found", user_name)
        
        # Step 4: Execute all attendance marking concurrently
        if all_attendance_tasks:
            log("INFO", f"Processing {total_pending} attendance records concurrently across all users")
            
            # Execute all attendance tasks at once
            attendance_results = await asyncio.gather(*[task for _, task in all_attendance_tasks])
            
            # Count successes per user
            user_success_count = {}
            for i, (user_name, _) in enumerate(all_attendance_tasks):
                if user_name not in user_success_count:
                    user_success_count[user_name] = 0
                if attendance_results[i]:
                    user_success_count[user_name] += 1
            
            # Report results
            for user_name in active_users:
                success_count = user_success_count.get(user_name, 0)
                if success_count > 0:
                    log("SUCCESS", f"Successfully marked {success_count} attendance records", user_name)
        else:
            log("INFO", "No attendance records to process for any user")
        
        log("SUCCESS", "Attendance cycle completed for all users")
        print()  # Empty line for readability

    async def start_all_users(self):
        """Start attendance processing for all users together"""
        # Login all users
        log("INFO", "Starting Multi-User Attendance Bot")
        self.user_sessions = login_all_users()
        
        if not self.user_sessions:
            log("ERROR", "No users logged in successfully - terminating application")
            return
        
        log("SUCCESS", f"Successfully authenticated {len(self.user_sessions)} users")
        log("INFO", "Starting unified attendance processing cycle")
        print()  # Empty line for readability
        
        # Run unified processing cycle
        try:
            while True:
                await self.process_all_users_cycle()
                
                # Wait before next cycle
                log("DEBUG", "Waiting 1 second before next cycle")
                await asyncio.sleep(1)
                
        except Exception as e:
            log("ERROR", f"Critical error in attendance processing: {e}")
    
    def stop_all_users(self):
        """Stop all running user tasks"""
        log("INFO", "Stopping all user tasks")
        for user_name, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                log("INFO", "Task stopped", user_name)

async def main():
    """Main function to run the multi-user attendance bot"""
    bot = MultiUserAttendanceBot()
    
    try:
        await bot.start_all_users()
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Received interrupt signal - shutting down gracefully")
        bot.stop_all_users()
    except Exception as e:
        log("ERROR", f"Unexpected error in main application: {e}")
        bot.stop_all_users()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()  # New line for readability
        log("INFO", "Multi-User Attendance Bot terminated successfully")
    except Exception as e:
        log("ERROR", f"Fatal application error: {e}")