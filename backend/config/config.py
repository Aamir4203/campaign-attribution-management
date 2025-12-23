import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Enterprise-grade configuration manager for CAM application.
    Loads configuration from YAML files with environment override support.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize ConfigManager with optional custom config file.

        Args:
            config_file: Optional path to custom config file
        """
        self._config: Dict[str, Any] = {}
        self._config_file = config_file
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file with environment overrides"""
        # Determine config file path
        if self._config_file:
            config_path = Path(self._config_file)
        else:
            config_path = Path(__file__).parent.parent.parent / "shared" / "config" / "app.yaml"

        try:
            logger.info(f"Loading configuration from: {config_path}")

            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(config_path, 'r') as file:
                self._config = yaml.safe_load(file)

            logger.info("✅ Configuration loaded successfully")

            # Apply environment overrides
            self._apply_environment_overrides()

        except FileNotFoundError as e:
            logger.error(f"❌ Configuration file not found: {e}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"❌ Invalid YAML configuration: {e}")
            raise ValueError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            logger.error(f"❌ Error loading configuration: {e}")
            raise ValueError(f"Error loading configuration: {e}")

    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configuration"""
        env_mappings = {
            'CAM_DB_HOST': ['database', 'host'],
            'CAM_DB_PORT': ['database', 'port'],
            'CAM_DB_NAME': ['database', 'database'],
            'CAM_DB_USER': ['database', 'username'],
            'CAM_DB_PASSWORD': ['database', 'password'],
            'CAM_DEBUG': ['debug'],
            'CAM_ENVIRONMENT': ['environment'],
            'CAM_API_PORT': ['backend', 'development', 'port'],
            'CAM_FRONTEND_PORT': ['frontend', 'development', 'port'],
        }

        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Navigate to nested config and set value
                config_ref = self._config
                for key in config_path[:-1]:
                    if key not in config_ref:
                        config_ref[key] = {}
                    config_ref = config_ref[key]

                # Convert value to appropriate type
                if config_path[-1] == 'port':
                    value = int(value)
                elif config_path[-1] == 'debug':
                    value = value.lower() in ('true', '1', 'yes')

                config_ref[config_path[-1]] = value
                logger.info(f"🔧 Environment override applied: {env_var} = {value}")

    def get_database_config(self) -> Dict[str, Any]:
        """Get complete database configuration"""
        return self._config.get('database', {})
    
    def get_database_connection_string(self) -> str:
        """Get database connection string for SQLAlchemy"""
        db_config = self.get_database_config()
        return (f"postgresql://{db_config.get('username')}:{db_config.get('password')}"
                f"@{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}")

    def get_database_credentials(self) -> Dict[str, Any]:
        """Get database credentials for psycopg2 connection"""
        db_config = self.get_database_config()
        return {
            'host': db_config.get('host'),
            'port': db_config.get('port'),
            'database': db_config.get('database'),
            'user': db_config.get('username'),
            'password': db_config.get('password')
        }

    def get_table_names(self) -> Dict[str, str]:
        """Get all table names"""
        return self._config.get('database', {}).get('tables', {})

    def get_table_name(self, table_key: str) -> str:
        """Get specific table name by key"""
        return self.get_table_names().get(table_key, '')

    def get_external_databases(self) -> Dict[str, Dict[str, Any]]:
        """Get external database configurations"""
        return self._config.get('external_databases', {})

    def get_external_db_config(self, db_key: str) -> Dict[str, Any]:
        """Get specific external database configuration"""
        return self.get_external_databases().get(db_key, {})

    def get_file_paths(self) -> Dict[str, str]:
        """Get file system path configurations"""
        return self._config.get('file_paths', {})

    def get_file_path(self, path_key: str, **kwargs) -> str:
        """Get specific file path with optional formatting"""
        path_template = self.get_file_paths().get(path_key, '')
        if kwargs:
            return path_template.format(**kwargs)
        return path_template

    def get_alerts_config(self) -> Dict[str, str]:
        """Get alert configuration"""
        return self._config.get('alerts', {})

    def get_upload_config(self) -> Dict[str, Any]:
        """Get file upload configuration"""
        return self._config.get('constants', {}).get('upload', {})

    def get_features(self) -> Dict[str, bool]:
        """Get feature flag configuration"""
        return self._config.get('features', {})

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.get_features().get(feature_name, False)

    def get_app_constants(self) -> Dict[str, Any]:
        """Get application constants"""
        return self._config.get('constants', {})
    
    def get_request_constants(self) -> Dict[str, Any]:
        """Get request-specific constants"""
        return self.get_app_constants().get('requests', {})

    def get_default_old_percentage(self) -> int:
        """Get default old delivered percentage"""
        return self.get_request_constants().get('defaultOldDeliveredPercentage', 65)

    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self.get_app_constants().get('api', {})

    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        return self.get_api_config().get('cors', {})

    def get_cors_origins(self) -> List[str]:
        """Get allowed CORS origins"""
        return self.get_cors_config().get('allowedOrigins', [])

    def get_theme_config(self) -> Dict[str, Any]:
        """Get ZETA theme configuration"""
        return self._config.get('theme', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self._config.get('security', {})
    
    def get_environment(self) -> str:
        """Get environment setting"""
        return self._config.get('environment', 'development')
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self._config.get('debug', False)
    
    def get_backend_config(self) -> Dict[str, Any]:
        """Get backend server configuration"""
        return self._config.get('backend', {})

    def get_frontend_config(self) -> Dict[str, Any]:
        """Get frontend configuration"""
        return self._config.get('frontend', {})

    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self._config.get('logging', {})

    def get_full_config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary"""
        return self._config.copy()

    def validate_config(self) -> bool:
        """Validate critical configuration settings"""
        try:
            # Check database config
            db_config = self.get_database_config()
            required_db_keys = ['host', 'port', 'database', 'username', 'password']
            for key in required_db_keys:
                if not db_config.get(key):
                    logger.error(f"❌ Missing database configuration: {key}")
                    return False

            # Check table names
            table_config = self.get_table_names()
            required_tables = ['clients', 'requests', 'qa_stats', 'tracking']
            for table in required_tables:
                if not table_config.get(table):
                    logger.error(f"❌ Missing table configuration: {table}")
                    return False

            logger.info("✅ Configuration validation passed")
            return True

        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False

# Global config instance
_config_instance = None

def get_config() -> ConfigManager:
    """Get global configuration instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance

def reload_config(config_file: Optional[str] = None) -> ConfigManager:
    """Reload configuration from file"""
    global _config_instance
    _config_instance = ConfigManager(config_file)
    return _config_instance

