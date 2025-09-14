import asyncio
from timetable import *
from markit import *
from sid import *
import os

terminal_width = os.get_terminal_size().columns
os.system('clear' if os.name == 'posix' else 'cls')
pilcrow = "¶"
padding = (terminal_width - len(pilcrow)) // 2
centered_pilcrow = " " * padding + pilcrow

print("\n"+centered_pilcrow+"\n")

print("Welcome to Camuflaged v1.5.0 - gregnald\n".center(terminal_width, " "))
print("(Press Ctrl+C to exit)\n".center(terminal_width, " "))
print("For educational purposes only".center(terminal_width, "-"))

print("Enter your college email: ",end="")
# email = "e23cseu0035@bennett.edu.in"
email = "e23cseu0705@bennett.edu.in"
print("Enter your password: ",end="")
# password = "Bu@#123456"
password = "Reo@#2004"
if not email or not password:
    print("Email and password cannot be empty.")
    exit(1)

if(login(email,password)):
    print("Login successful!")
else:
    print("Login failed. Please check your email and password.")
    exit(1)

with open('user_data.json','r') as f:
    data = json.load(f)
    sid = data['sid']
    json_payload = data['data']['progressionData'][0]
    stuId = data['data']['logindetails']['Student'][0]['StuID']


async def extract_pending_attendance_classes():
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

async def autc():
    while True:
        try:
            sid = login(email,password, flag=False)
            pending = await extract_pending_attendance_classes()
            #print(type(pending))
            # print('GO')
            print("\033[A\033[K", end="")
            print(f"Starting to mark attendance... [{sid}]")
            tasks = []
            for i in pending.values():
                print(i[0])
                tasks.append(asyncio.create_task(mark_attendance(sid, i[0], stuId)))
            if tasks:
                await asyncio.gather(*tasks)
                print("Attendance marked successfully.")
                print("\n")
            await asyncio.sleep(1)
        except TimeoutError:
            print("[ERROR] Request timed out. Please check your internet connection.")
            continue
        except Exception as e:
            print(f"[ERROR] While fetching attendance: {e}")
            continue
if __name__ == "__main__":
    try:
        asyncio.run(autc())
    except KeyboardInterrupt:
        print("\nStopping the Script now...")
        exit(0)
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
        exit(1)
