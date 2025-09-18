import asyncio
import json
import os
from datetime import datetime
from timetable import *
from markit import *
from sid import *

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
            print(f"[ERROR] while extracting periods for {user_data.get('user_name', 'unknown')}: {e}")
        
        return result
    
    async def process_user_attendance(self, user_name, user_data):
        """Process attendance for a single user"""
        print(f"🔄 Starting attendance processing for {user_name}")
        
        while True:
            try:
                # Re-login to get fresh session
                email = user_data['email']
                password = None
                
                # Get password from config
                users_config = load_users_config()
                for user in users_config:
                    if user['name'] == user_name:
                        password = user['password']
                        break
                
                if not password:
                    print(f"❌ Could not find password for {user_name}")
                    break
                
                # Get fresh session ID
                sid = login(email, password, user_name, return_sid_only=True)
                if not sid:
                    print(f"❌ Re-login failed for {user_name}")
                    await asyncio.sleep(5)
                    continue
                
                # Update session in user data
                user_data['sid'] = sid
                
                # Get pending classes
                pending = await self.extract_pending_attendance_classes(user_data)
                
                if pending:
                    print(f"📝 Found {len(pending)} pending classes for {user_name}")
                    
                    # Get student ID
                    stuId = user_data['data']['logindetails']['Student'][0]['StuID']
                    
                    # Create tasks for marking attendance
                    tasks = []
                    for attendance_info in pending.values():
                        attendance_id = attendance_info[0]
                        tasks.append(asyncio.create_task(
                            mark_attendance(sid, attendance_id, stuId)
                        ))
                    
                    if tasks:
                        await asyncio.gather(*tasks)
                        print(f"✅ Processed {len(tasks)} attendance records for {user_name}")
                else:
                    print(f"No pending attendance for {user_name}")
                
                # Wait before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"[ERROR] Processing attendance for {user_name}: {e}")
                await asyncio.sleep(5)
    
    async def start_all_users(self):
        """Start attendance processing for all users"""
        # Login all users
        print("🚀 Starting multi-user attendance bot...")
        self.user_sessions = login_all_users()
        
        if not self.user_sessions:
            print("❌ No users logged in successfully. Exiting.")
            return
        
        print(f"✅ Successfully logged in {len(self.user_sessions)} users")
        
        # Create tasks for each user
        tasks = []
        for user_name, user_data in self.user_sessions.items():
            task = asyncio.create_task(
                self.process_user_attendance(user_name, user_data)
            )
            self.running_tasks[user_name] = task
            tasks.append(task)
        
        # Run all user tasks concurrently
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"[ERROR] in start_all_users: {e}")
    
    def stop_all_users(self):
        """Stop all running user tasks"""
        print("🛑 Stopping all user tasks...")
        for user_name, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                print(f"Stopped task for {user_name}")

async def main():
    """Main function to run the multi-user attendance bot"""
    bot = MultiUserAttendanceBot()
    
    try:
        await bot.start_all_users()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal. Stopping...")
        bot.stop_all_users()
    except Exception as e:
        print(f"[ERROR] Unexpected error in main: {e}")
        bot.stop_all_users()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")