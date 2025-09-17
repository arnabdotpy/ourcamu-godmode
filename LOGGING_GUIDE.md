# OURCAMU Attendance Bot - Logging Guide

## Overview
The attendance bot now features a comprehensive logging system that provides detailed monitoring and debugging capabilities for multiple user attendance tracking.

## Logging Features

### 1. Multi-Level Logging
- **DEBUG**: Detailed information for debugging (session IDs, API calls, etc.)
- **INFO**: General information about bot operations
- **WARNING**: Important notifications that don't stop execution
- **ERROR**: Error conditions that might affect functionality

### 2. Optimized Session Management
- **Single Login**: Each user logs in only once at startup
- **Session Reuse**: Existing sessions are reused throughout the process
- **Smart Refresh**: Sessions are only refreshed when necessary (authentication errors or validation failures)
- **Periodic Validation**: Sessions are validated every 5 minutes to ensure they're still active
- **Error-Driven Refresh**: Sessions are refreshed automatically when session-related errors are detected

### 3. Multi-File Logging Structure
```
logs/
├── attendance_main.log       # Main application logs
├── attendance_arkade.log     # User-specific logs for Arkade
├── attendance_arnab.log      # User-specific logs for Arnab
├── attendance_abhshek.log    # User-specific logs for Abhshek
├── attendance_piyush.log     # User-specific logs for Piyush
└── attendance_grisha.log     # User-specific logs for Grisha
```

### 3. Log Rotation
- **Main logs**: 5MB max size, 3 backup files
- **User logs**: 2MB max size, 2 backup files
- Automatic rotation prevents disk space issues

### 4. Thread-Safe Logging
- Each user thread has its own logger
- No log mixing between different users
- Thread names included in log entries

## Log Levels in Console vs Files

### Console Output
- **Main Logger**: INFO level and above
- **User Loggers**: WARNING level and above (to reduce console spam)
- Clean, readable format with timestamps

### File Output
- **All Loggers**: DEBUG level and above
- Detailed format with thread names and full timestamps
- Complete audit trail of all operations

## Sample Log Entries

### Main Application Log (attendance_main.log)
```
2024-12-19 10:30:15 - attendance_main - INFO - [MainThread] - === OURCAMU Attendance Bot Started ===
2024-12-19 10:30:15 - attendance_main - INFO - [MainThread] - Configured users: 5
2024-12-19 10:30:16 - attendance_main - INFO - [MainThread] - Initializing session for Arkade (e23cseu0688@bennett.edu.in)...
2024-12-19 10:30:17 - attendance_main - INFO - [MainThread] - Login successful for Arkade!
2024-12-19 10:30:18 - attendance_main - INFO - [MainThread] - Started attendance thread for Arkade
```

### User-Specific Log (attendance_arkade.log)
```
2024-12-19 10:30:17 - INFO - [MainThread] - Session initialized successfully for Arkade
2024-12-19 10:30:17 - DEBUG - [MainThread] - Session ID: s%3AabcdefV...
2024-12-19 10:30:17 - DEBUG - [MainThread] - Student ID: 12345
2024-12-19 10:30:18 - INFO - [AttendanceThread-Arkade] - Thread started successfully
2024-12-19 10:30:18 - INFO - [AttendanceThread-Arkade] - Starting attendance monitoring loop for Arkade
2024-12-19 10:30:18 - DEBUG - [AttendanceThread-Arkade] - Using existing session: s%3AabcdefV...
2024-12-19 10:30:19 - DEBUG - [AttendanceThread-Arkade] - Fetching timetable data...
2024-12-19 10:30:20 - DEBUG - [AttendanceThread-Arkade] - Found 6 periods in timetable
2024-12-19 10:30:20 - DEBUG - [AttendanceThread-Arkade] - Found pending attendance: Period 123, Attendance ID: ATT456
2024-12-19 10:30:20 - INFO - [AttendanceThread-Arkade] - Found 2 pending attendance classes
2024-12-19 10:30:20 - INFO - [AttendanceThread-Arkade] - Starting to mark attendance for 2 classes...
2024-12-19 10:30:21 - DEBUG - [AttendanceThread-Arkade] - Attendance marked successfully: SUCCESS for attendance ID ATT456
2024-12-19 10:30:21 - INFO - [AttendanceThread-Arkade] - Attendance marking completed: 2/2 successful
2024-12-19 10:35:18 - DEBUG - [AttendanceThread-Arkade] - Performing periodic session validation...
2024-12-19 10:35:19 - DEBUG - [AttendanceThread-Arkade] - Session validation passed
2024-12-19 11:15:18 - DEBUG - [AttendanceThread-Arkade] - Performing periodic session validation...
2024-12-19 11:15:19 - WARNING - [AttendanceThread-Arkade] - Session validation failed, refreshing session...
2024-12-19 11:15:20 - INFO - [AttendanceThread-Arkade] - Session refreshed successfully (refresh #1): s%3Axyz789W...
```

## Monitoring Tips

### Real-time Monitoring
```bash
# Watch main application logs
tail -f logs/attendance_main.log

# Watch specific user logs
tail -f logs/attendance_arnab.log

# Watch all logs simultaneously
tail -f logs/*.log
```

### Session Management Monitoring
```bash
# Monitor session refreshes across all users
grep -i "session refresh" logs/attendance_*.log

# Check session validation frequency
grep -i "session validation" logs/attendance_*.log

# Count total session refreshes per user
grep -c "Session refreshed successfully" logs/attendance_*.log

# Find session-related errors
grep -i "session.*error\|failed.*session" logs/attendance_*.log
```

### Error Investigation
```bash
# Find all errors in main log
grep -i "ERROR" logs/attendance_main.log

# Find warnings and errors for specific user
grep -E "(WARNING|ERROR)" logs/attendance_arkade.log

# Search for specific issues
grep -i "timeout" logs/*.log
grep -i "failed" logs/*.log
```

### Performance Analysis
```bash
# Count successful attendance markings
grep -c "Attendance marked successfully" logs/attendance_*.log

# Check session refresh frequency
grep -c "Session refreshed" logs/attendance_*.log
```

## Configuration

The logging system is automatically configured when the bot starts. Key settings:

- **Log Directory**: `logs/` (created automatically)
- **Date Format**: `YYYY-MM-DD HH:MM:SS`
- **Thread Safety**: Built-in thread-safe handlers
- **Encoding**: UTF-8 for international characters

## Benefits

1. **Debugging**: Detailed logs help identify issues quickly
2. **Monitoring**: Track bot performance and success rates
3. **Auditing**: Complete history of all operations
4. **Troubleshooting**: Separate logs per user for easier diagnosis
5. **Performance**: Monitor attendance marking efficiency
6. **Compliance**: Detailed audit trails for institutional requirements

## Best Practices

1. **Regular Monitoring**: Check logs daily for any warnings or errors
2. **Log Rotation**: Logs automatically rotate to prevent disk space issues
3. **Backup**: Consider backing up log files for long-term analysis
4. **Privacy**: Log files contain session information - keep them secure
5. **Analysis**: Use log analysis tools for patterns and trends

The enhanced logging system provides complete visibility into the bot's operations while maintaining clean console output for daily use.