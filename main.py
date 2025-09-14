import asyncio
import threading
import json
import time
import os
from timetable import *
from markit import *
from sid import *

terminal_width = os.get_terminal_size().columns
os.system('clear' if os.name == 'posix' else 'cls')
pilcrow = "¶"
padding = (terminal_width - len(pilcrow)) // 2
centered_pilcrow = " " * padding + pilcrow

print("\n"+centered_pilcrow+"\n")
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
            print(f"[{self.name}] Logging in...")
            login_result = login(self.email, self.password)
            
            if login_result:
                # Read the user data that was saved
                with open('user_data.json', 'r') as f:
                    data = json.load(f)
                    self.sid = data['sid']
                    self.json_payload = data['data']['progressionData'][0]
                    self.student_id = data['data']['logindetails']['Student'][0]['StuID']
                    
                self.is_logged_in = True
                print(f"[{self.name}] Login successful! Student ID: {self.student_id}")
                return True
            else:
                print(f"[{self.name}] Login failed!")
                return False
                
        except Exception as e:
            print(f"[{self.name}] Error during authentication: {e}")
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
            print(f"[{self.name}] Error extracting periods: {e}")
            
        return result
    
    async def mark_user_attendance(self):
        """Mark attendance for this user"""
        try:
            if not self.is_logged_in:
                # Try to re-authenticate using sid method
                self.sid = login(self.email, self.password, flag=False)
                if not self.sid:
                    print(f"[{self.name}] Re-authentication failed")
                    return False
            
            pending = await self.extract_pending_attendance_classes()
            
            if not pending:
                print(f"[{self.name}] No pending attendance found")
                return True
                
            print(f"[{self.name}] Found {len(pending)} pending attendance(s)")
            
            tasks = []
            for attendance_info in pending.values():
                attendance_id = attendance_info[0]
                print(f"[{self.name}] Marking attendance for ID: {attendance_id}")
                tasks.append(mark_attendance(self.sid, attendance_id, self.student_id))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for result in results if result and not isinstance(result, Exception))
                print(f"[{self.name}] Successfully marked {success_count}/{len(tasks)} attendances")
                
            return True
            
        except Exception as e:
            print(f"[{self.name}] Error marking attendance: {e}")
            return False
    
    async def run_attendance_loop(self):
        """Main loop for this user's attendance marking"""
        while True:
            try:
                success = await self.mark_user_attendance()
                if success:
                    print(f"[{self.name}] Attendance cycle completed")
                else:
                    print(f"[{self.name}] Attendance cycle failed")
                    
                await asyncio.sleep(1)  # Wait before next cycle
                
            except Exception as e:
                print(f"[{self.name}] Error in attendance loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

def run_user_worker(user_info):
    """Function to run in separate thread for each user"""
    try:
        worker = AttendanceWorker(user_info)
        
        # Authenticate first
        if not worker.authenticate():
            print(f"[{worker.name}] Failed to authenticate, skipping this user")
            return
            
        # Run the attendance loop
        asyncio.run(worker.run_attendance_loop())
        
    except KeyboardInterrupt:
        print(f"[{user_info['name']}] Stopping...")
    except Exception as e:
        print(f"[{user_info['name']}] Worker error: {e}")

def main():
    """Main function to start all user threads"""
    threads = []
    
    print(f"\nStarting attendance marking for {len(USERS)} users...\n")
    
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
            
            # Small delay between starting threads to avoid overwhelming the server
            time.sleep(0.5)
        
        print(f"All {len(threads)} worker threads started successfully!")
        print("Press Ctrl+C to stop all workers...\n")
        
        # Keep main thread alive
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("\n\nStopping all workers...")
        # Threads will automatically stop since they're daemon threads
        print("All workers stopped.")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
