import httpx

async def mark_attendance(session_id: str, attendance_id: str, student_id: str):
    url = "https://student.bennetterp.camu.in/api/Attendance/record-online-attendance"
    headers = {
        "Cookie": f"connect.sid={session_id}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://student.bennetterp.camu.in",
        "Referer": "https://student.bennetterp.camu.in/v2/timetable",
    }
    payload = {
        "attendanceId": attendance_id,
        "isMeetingStarted": True,
        "StuID": student_id,
        "offQrCdEnbld": True
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            pass # print(data)
            if data["output"]["data"] is not None:
                code = data["output"]["data"]["code"]
                print(code)
                if code == "SUCCESS":
                    print(f"✅ [SUCCESS] Marked attendance for student: {student_id}")
                    return True
                elif code == "ATTENDANCE_ALREADY_RECORDED":
                    print(f"✅ [INFO] Attendance already recorded for student: {student_id}")
                    return True
                else:
                    print(f"❌ [FAIL] Could not mark attendance for student: {student_id}. Reason: {data['output']['data']['message']}")
                    return False
            elif data["output"]["errors"] is not None:
                code = data["output"]["errors"]["code"]
                if code == "INVLD_QR":
                    print(f"❌ [FAIL] Could not mark attendance for student: {student_id}. Reason: {data['output']['errors']['message']}")
                return False
            else:
                pass # print(f"[FAIL] Invalid response for student: {student_id}")
                print(f"❌ [FAIL] {data}")
                return False
    except Exception as e:
        pass # print(f"[ERROR] While marking for student {student_id}: {e}")
        return False
