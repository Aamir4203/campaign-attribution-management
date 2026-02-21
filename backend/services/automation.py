"""
Simple automation service to run requestPicker.sh every 15 seconds
Auto-starts with Flask application
"""
import subprocess
import threading
import time
import logging
import os

logger = logging.getLogger(__name__)


class Automation:
    """Simple scheduler that runs requestPicker.sh every 15 seconds"""

    def __init__(self):
        self.running = False
        self.thread = None

        # Load configuration
        try:
            from config.config import get_config
            config = get_config()
            automation_config = config.get_config_value('automation', {})

            self.script_path = automation_config.get('script_path', './SCRIPTS/requestPicker.sh')
            self.interval = automation_config.get('interval_seconds', 15)
            self.timeout = automation_config.get('script_timeout_seconds', 300)
        except Exception as e:
            logger.warning(f"Failed to load automation config, using defaults: {e}")
            self.script_path = './SCRIPTS/requestPicker.sh'
            self.interval = 15
            self.timeout = 300

    def start(self):
        """Start the automation scheduler"""
        if self.running:
            logger.warning("Automation already running")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info(f"✅ Automation started - Running {self.script_path} every {self.interval}s")
        return True

    def stop(self):
        """Stop the automation scheduler"""
        if not self.running:
            logger.warning("Automation not running")
            return False

        self.running = False
        logger.info("⏹️ Automation stopped")
        return True

    def _loop(self):
        """Main loop - runs script every interval seconds"""
        while self.running:
            try:
                logger.debug(f"Running {self.script_path}")
                result = subprocess.run(
                    ['bash', self.script_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                if result.returncode != 0:
                    logger.warning(f"Script exited with code {result.returncode}")
                    if result.stderr:
                        logger.warning(f"stderr: {result.stderr[:500]}")

            except subprocess.TimeoutExpired:
                logger.error(f"Script timeout ({self.timeout} seconds)")
            except Exception as e:
                logger.error(f"Error running script: {e}")

            # Sleep for interval
            time.sleep(self.interval)

    def status(self):
        """Get current status"""
        return {
            'running': self.running,
            'interval_seconds': self.interval,
            'script_path': self.script_path
        }


# Global instance
_automation = Automation()


def start():
    """Start automation"""
    return _automation.start()


def stop():
    """Stop automation"""
    return _automation.stop()


def status():
    """Get automation status"""
    return _automation.status()
