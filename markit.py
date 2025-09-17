import httpx
import logging

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

    # Get logger for current thread context
    logger = logging.getLogger('attendance_main')

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            
            if data["output"]["data"] is not None:
                code = data["output"]["data"]["code"]
                if code in ["SUCCESS", "ATTENDANCE_ALREADY_RECORDED"]:
                    logger.debug(f"Attendance marked successfully: {code} for attendance ID {attendance_id}")
                    return True
                else:
                    logger.warning(f"Unexpected response code: {code} for attendance ID {attendance_id}")
                    return False
            else:
                logger.error(f"Invalid response for student: {student_id}, attendance ID: {attendance_id}")
                return False
    except Exception as e:
        logger.error(f"Error while marking attendance for student {student_id}: {e}")
        return False
