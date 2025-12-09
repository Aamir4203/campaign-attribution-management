# PYTHON INTEGRATION - SHELL CALLS

## Simple Solution

Python scripts call existing shell tracking functions using subprocess calls.

## Basic Template for Python Scripts

```python
#!/usr/bin/env python3

import sys
import os
import subprocess

def track_process(request_id, module_name):
    """Call existing shell tracking function"""
    subprocess.run([
        'bash', '-c', 
        f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "{module_name}"'
    ], cwd=os.path.dirname(__file__), check=False)

def mark_failed(request_id, module_name, error_msg):
    """Call shell function to mark request as failed"""
    subprocess.run([
        'bash', '-c', 
        f'source ./config.properties && source $TRACKING_HELPER && mark_request_failed {request_id} "{module_name}" "{error_msg}"'
    ], cwd=os.path.dirname(__file__), check=False)

def main():
    request_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not request_id:
        print("Error: Request ID required")
        sys.exit(1)
    
    try:
        # Track this process
        track_process(request_id, "MODULE_NAME")
        
        # Your existing Python code here
        # ...existing logic...
        
    except Exception as e:
        mark_failed(request_id, "MODULE_NAME", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
```


## Integration Examples

### rltpDataPulling.py (with threads):

```python
import subprocess
import threading

def track_process(request_id, module_name):
    subprocess.run(['bash', '-c', f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "{module_name}"'], cwd=os.path.dirname(__file__), check=False)

def main():
    request_id = sys.argv[1]
    
    # Track main process
    track_process(request_id, "RLTP_MAIN")
    
    # Create threads
    for i in range(5):
        thread = threading.Thread(target=process_thread, args=(request_id, i))
        thread.start()

def process_thread(request_id, thread_num):
    # Track this thread
    track_process(request_id, f"RLTP_THREAD_T{thread_num}")
    # ...existing thread logic...
```

### delete_partitions.py:

```python
import subprocess

def main():
    request_id = sys.argv[1]
    
    # Track process
    subprocess.run(['bash', '-c', f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "DELETE_PARTITION"'], cwd=os.path.dirname(__file__), check=False)
    
    # ...existing partition deletion code...
```

## Summary

- Uses existing trackingHelper.sh functions
- Simple subprocess calls to shell infrastructure
- No additional files or dependencies needed
