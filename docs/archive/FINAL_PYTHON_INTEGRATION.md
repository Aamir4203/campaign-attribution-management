# PYTHON INTEGRATION - DIRECT SUBPROCESS CALLS

## Simple Solution

Python scripts call existing shell tracking functions using direct subprocess calls.

## Basic Template for Python Scripts

```python
#!/usr/bin/env python3

import sys
import os
import subprocess

def main():
    request_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not request_id:
        print("Error: Request ID required")
        sys.exit(1)
    
    try:
        # Track this process directly
        subprocess.run([
            'bash', '-c', 
            f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "MODULE_NAME"'
        ], cwd=os.path.dirname(__file__), check=False)
        
        # Your existing Python code here
        # ...existing logic...
        
    except Exception as e:
        # Mark failed directly
        subprocess.run([
            'bash', '-c', 
            f'source ./config.properties && source $TRACKING_HELPER && mark_request_failed {request_id} "MODULE_NAME" "{str(e)}"'
        ], cwd=os.path.dirname(__file__), check=False)
        sys.exit(1)

if __name__ == "__main__":
    main()
```


## Integration Examples

### rltpDataPulling.py (with threads):

```python
import subprocess
import threading
import sys
import os

def main():
    request_id = sys.argv[1]
    
    # Track main process directly
    subprocess.run(['bash', '-c', f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "RLTP_MAIN"'], cwd=os.path.dirname(__file__), check=False)
    
    # Create threads
    for i in range(5):
        thread = threading.Thread(target=process_thread, args=(request_id, i))
        thread.start()

def process_thread(request_id, thread_num):
    # Track this thread directly
    subprocess.run(['bash', '-c', f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "RLTP_THREAD_T{thread_num}"'], cwd=os.path.dirname(__file__), check=False)
    # ...existing thread logic...
```

### delete_partitions.py:

```python
import subprocess
import sys
import os

def main():
    request_id = sys.argv[1]
    
    # Track process directly
    subprocess.run(['bash', '-c', f'source ./config.properties && source $TRACKING_HELPER && append_process_id {request_id} "DELETE_PARTITION"'], cwd=os.path.dirname(__file__), check=False)
    
    # ...existing partition deletion code...
```

## Summary

- Uses existing trackingHelper.sh functions
- Simple subprocess calls to shell infrastructure
- No additional files or dependencies needed
