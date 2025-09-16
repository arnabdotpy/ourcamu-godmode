import asyncio
import threading
import time
from timetable import *
from markit import *
from sid import *

print("FUCK YOU CAMU")

# List of users - add your credentials here
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

class AttendanceWorker:
    def __init__(self, user_info):
        self.email = user_info["email"]
        self.password = user_info["password"]
        self.name = user_info["name"]
        self.sid = None
        self.student_id = None
        self.json_payload = None
        self.is_logged_in = False
        self.lock = threading.Lock()
        
    def authenticate(self):
        """Authenticate user and get session details"""
        try:
            log_message("INFO", self.email, f"Starting authentication for {self.name}")
            login_result = login(self.email, self.password)
            
            if login_result:
                # Get user data directly from the individual user file
                user_data = get_user_data_by_email(self.email)
                if user_data:
                    self.sid = user_data['sid']
                    self.json_payload = user_data['json_payload']
                    self.student_id = user_data['student_id']
                    
                    self.is_logged_in = True
                    log_message("SUCCESS", self.email, f"{self.name} authenticated successfully! Student ID: {self.student_id}")
                    return True
                else:
                    log_message("ERROR", self.email, f"Failed to load user data for {self.name}")
                    return False
            else:
                log_message("ERROR", self.email, f"Authentication failed for {self.name}")
                return False
                
        except Exception as e:
            log_message("ERROR", self.email, f"Error during authentication for {self.name}: {e}")
            return False
    
    async def extract_pending_attendance_classes(self):
        """Extract pending attendance classes for this user"""
        result = {}
        try:
            response = fetch_timetable_headerless(self.sid, self.json_payload)
            periods = response["output"]["data"][0]["Periods"]
            
            for cls in periods:
                if "attendanceId" in cls and not cls.get("isAttendanceSaved"):
                    result[cls["PeriodId"]] = [cls["attendanceId"], cls["isAttendanceSaved"]]
                    
        except Exception as e:
            log_message("ERROR", self.email, f"Error extracting periods for {self.name}: {e}")
            
        return result
    
    async def mark_user_attendance(self):
        """Mark attendance for this user"""
        try:
            if not self.is_logged_in:
                # Try to re-authenticate using sid method
                self.sid = login(self.email, self.password, flag=False)
                if not self.sid:
                    log_message("ERROR", self.email, f"Re-authentication failed for {self.name}")
                    return False
            
            pending = await self.extract_pending_attendance_classes()
            
            if not pending:
                log_message("INFO", self.email, f"No pending attendance found for {self.name}")
                return True
                
            log_message("INFO", self.email, f"Found {len(pending)} pending attendance(s) for {self.name}")
            
            tasks = []
            for attendance_info in pending.values():
                attendance_id = attendance_info[0]
                log_message("INFO", self.email, f"Marking attendance for ID: {attendance_id} ({self.name})")
                tasks.append(mark_attendance(self.sid, attendance_id, self.student_id))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for result in results if result and not isinstance(result, Exception))
                log_message("SUCCESS", self.email, f"{self.name} successfully marked {success_count}/{len(tasks)} attendances")
                
            return True
            
        except Exception as e:
            log_message("ERROR", self.email, f"Error marking attendance for {self.name}: {e}")
            return False
    
    async def run_attendance_loop(self):
        """Main loop for this user's attendance marking"""
        while True:
            try:
                success = await self.mark_user_attendance()
                if success:
                    log_message("INFO", self.email, f"Attendance cycle completed for {self.name}")
                else:
                    log_message("WARN", self.email, f"Attendance cycle failed for {self.name}")
                    
                await asyncio.sleep(1)  # Wait before next cycle
                
            except Exception as e:
                log_message("ERROR", self.email, f"Error in attendance loop for {self.name}: {e}")
                await asyncio.sleep(5)  # Wait longer on error

def run_user_worker(user_info):
    """Function to run in separate thread for each user"""
    try:
        worker = AttendanceWorker(user_info)
        
        # Authenticate first
        if not worker.authenticate():
            log_message("ERROR", user_info['email'], f"Failed to authenticate {user_info['name']}, skipping this user")
            return
            
        # Run the attendance loop
        asyncio.run(worker.run_attendance_loop())
        
    except KeyboardInterrupt:
        log_message("INFO", user_info['email'], f"Stopping worker for {user_info['name']}...")
    except Exception as e:
        log_message("ERROR", user_info['email'], f"Worker error for {user_info['name']}: {e}")

def main():
    """Main function to start all user threads"""
    threads = []
    
    log_message("INFO", None, f"Starting attendance marking system for {len(USERS)} users")
    
    try:
        # Create and start a thread for each user
        for user_info in USERS:
            thread = threading.Thread(
                target=run_user_worker, 
                args=(user_info,),
                name=f"Worker-{user_info['name']}"
            )
            thread.daemon = True  # Dies when main thread dies
            thread.start()
            threads.append(thread)
            log_message("INFO", None, f"Started worker thread for {user_info['name']}")
            
            # Small delay between starting threads to avoid overwhelming the server
            time.sleep(0.5)
        
        log_message("SUCCESS", None, f"All {len(threads)} worker threads started successfully!")
        log_message("INFO", None, "Press Ctrl+C to stop all workers...")
        
        # Keep main thread alive
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        log_message("INFO", None, "Stopping all workers...")
        # Threads will automatically stop since they're daemon threads
        log_message("INFO", None, "All workers stopped.")
    except Exception as e:
        log_message("ERROR", None, f"Error in main: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("INFO", None, "Exiting...")
    except Exception as e:
        log_message("FATAL", None, f"Fatal error: {e}")
