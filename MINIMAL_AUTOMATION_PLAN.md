# Minimal Automation Plan

## 🎯 Super Simple Solution

Just run `./SCRIPTS/requestPicker.sh` every 15 seconds.

---

## 📝 Implementation

### **Single File: `backend/services/automation.py`**

```python
import subprocess
import threading
import time
import logging
import os

logger = logging.getLogger(__name__)

class Automation:
    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return False
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("Automation started")
        return True

    def stop(self):
        self.running = False
        logger.info("Automation stopped")
        return True

    def _loop(self):
        while self.running:
            try:
                # Run script from project root
                subprocess.run(['bash', './SCRIPTS/requestPicker.sh'],
                             cwd=os.path.dirname(os.path.dirname(__file__)),
                             timeout=300)
            except Exception as e:
                logger.error(f"Script error: {e}")
            time.sleep(15)

    def status(self):
        return {'running': self.running}

# Global instance
_automation = Automation()

def start():
    return _automation.start()

def stop():
    return _automation.stop()

def status():
    return _automation.status()
```

---

### **Add 3 API Routes to existing `backend/routes/automation_routes.py`**

```python
from flask import Blueprint, jsonify
from services import automation

automation_bp = Blueprint('automation', __name__)

@automation_bp.route('/api/automation/status', methods=['GET'])
def get_status():
    return jsonify({'success': True, 'status': automation.status()})

@automation_bp.route('/api/automation/start', methods=['POST'])
def start():
    automation.start()
    return jsonify({'success': True})

@automation_bp.route('/api/automation/stop', methods=['POST'])
def stop():
    automation.stop()
    return jsonify({'success': True})
```

---

### **Update `backend/app.py`**

Add 2 lines:

```python
from routes.automation_routes import automation_bp
app.register_blueprint(automation_bp)

# Auto-start
from services import automation
automation.start()
```

---

## ✅ That's It!

**Total code: ~40 lines**

**What it does:**
- Runs `./SCRIPTS/requestPicker.sh` every 15 seconds
- Uses relative path from project root
- Auto-starts with Flask

**Test:**
```bash
# Check status
curl http://localhost:5000/api/automation/status

# Stop
curl -X POST http://localhost:5000/api/automation/stop

# Start
curl -X POST http://localhost:5000/api/automation/start
```

Done!
