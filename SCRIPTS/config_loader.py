#!/usr/bin/env python3
"""
Config Loader Module for APT SCRIPTS
Centralized configuration loading from YAML files.
Reusable across all Python processing scripts.
"""

import os
import yaml
from typing import Dict, Any, List
from multiprocessing import cpu_count


class ConfigLoader:
    """
    Singleton config loader for SCRIPTS.
    Loads configuration from config.yaml and provides easy access to settings.
    """

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ConfigLoader._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from unified YAML file."""
        # Path to unified config: SCRIPTS/../shared/config/app.yaml
        scripts_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(scripts_dir)
        config_path = os.path.join(project_root, 'shared', 'config', 'app.yaml')

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            ConfigLoader._config = yaml.safe_load(f)

    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration dictionary."""
        return ConfigLoader._config

    # ==================== Database ====================

    @property
    def db_host(self) -> str:
        return self._config['database']['host']

    @property
    def db_port(self) -> int:
        return self._config['database']['port']

    @property
    def db_name(self) -> str:
        # Support both 'name' (old SCRIPTS config) and 'database' (unified app.yaml)
        db_config = self._config.get('database', {})
        return db_config.get('name', db_config.get('database', ''))

    @property
    def db_user(self) -> str:
        # Support both 'user' (old) and 'username' (unified)
        db_config = self._config.get('database', {})
        return db_config.get('user', db_config.get('username', ''))

    @property
    def db_password(self) -> str:
        db_config = self._config.get('database', {})
        return db_config.get('password', '')

    # ==================== Tables ====================

    def _get_tables_config(self) -> Dict[str, str]:
        """Get tables config, supporting both old (top-level) and new (under database) structure."""
        # In unified app.yaml, tables are under database.tables
        # In old SCRIPTS config.yaml, tables were at top level
        if 'tables' in self._config:
            return self._config['tables']
        return self._config.get('database', {}).get('tables', {})

    @property
    def tables(self) -> Dict[str, str]:
        """Get all table names."""
        return self._get_tables_config()

    def get_table(self, key: str) -> str:
        """Get a specific table name by key."""
        return self._get_tables_config().get(key, '')

    @property
    def requests_table(self) -> str:
        return self._get_tables_config().get('requests', '')

    @property
    def clients_table(self) -> str:
        return self._get_tables_config().get('clients', '')

    @property
    def qa_stats_table(self) -> str:
        return self._get_tables_config().get('qa_stats', '')

    @property
    def tracking_table(self) -> str:
        return self._get_tables_config().get('tracking', '')

    @property
    def hards_table(self) -> str:
        return self._get_tables_config().get('hards', '')

    @property
    def unsubs_table(self) -> str:
        return self._get_tables_config().get('unsubs', '')

    def get_trt_table(self, request_id: str, client_name: str, week: str) -> str:
        """Generate TRT table name from template."""
        tables = self._get_tables_config()
        # Template might be in tables config or we use default
        template = tables.get('trt_table', 'apt_custom_{request_id}_{client_name}_{week}_trt_table')
        return template.format(
            request_id=request_id,
            client_name=client_name.lower(),
            week=week.lower()
        )

    def get_src_table(self, request_id: str, client_name: str, week: str) -> str:
        """Generate SRC table name from template."""
        tables = self._get_tables_config()
        template = tables.get('src_table', 'apt_custom_{request_id}_{client_name}_{week}_src_table')
        return template.format(
            request_id=request_id,
            client_name=client_name.lower(),
            week=week.lower()
        )

    def get_postback_table(self, request_id: str, client_name: str, week: str) -> str:
        """Generate POSTBACK table name from template."""
        tables = self._get_tables_config()
        template = tables.get('postback_table', 'apt_custom_{request_id}_{client_name}_{week}_postback_table')
        return template.format(
            request_id=request_id,
            client_name=client_name.upper(),
            week=week.upper()
        ).upper()

    # ==================== Processing ====================

    @property
    def max_workers(self) -> int:
        return min(cpu_count(), self._config['processing']['max_workers'])

    @property
    def chunk_size(self) -> int:
        return self._config['processing']['chunk_size']

    @property
    def max_retries(self) -> int:
        return self._config['processing']['max_retries']

    @property
    def retry_delay(self) -> int:
        return self._config['processing']['retry_delay_seconds']

    @property
    def audit_client_ids(self) -> List[int]:
        return self._config['processing']['audit_client_ids']

    @property
    def audit_trt_buffer(self) -> int:
        return self._config['processing']['audit_trt_buffer']

    def is_audit_client(self, client_id: int) -> bool:
        """Check if client is an audit client."""
        return client_id in self.audit_client_ids

    # ==================== Staging ====================

    @property
    def staging_enabled(self) -> bool:
        return self._config['staging']['enabled']

    @property
    def stage_prefix(self) -> str:
        return self._config['staging']['prefix']

    @property
    def stage_max_file_size(self) -> int:
        return self._config['staging']['max_file_size']

    @property
    def stage_compression(self) -> str:
        return self._config['staging']['compression']

    # ==================== Paths ====================

    @property
    def base_path(self) -> str:
        # Support both 'paths' (old) and 'file_paths' (new unified config)
        paths_config = self._config.get('file_paths', self._config.get('paths', {}))
        return paths_config.get('base', '')

    @property
    def request_processing_path(self) -> str:
        paths_config = self._config.get('file_paths', self._config.get('paths', {}))
        # In unified config, paths are relative; build absolute path
        rel_path = paths_config.get('request_processing', '')
        if rel_path and not rel_path.startswith('/'):
            return os.path.join(self.base_path, rel_path)
        return rel_path

    @property
    def python_modules_path(self) -> str:
        paths_config = self._config.get('file_paths', self._config.get('paths', {}))
        python_modules = paths_config.get('python_modules', '')
        # Return absolute path as-is, or build from base if relative
        if python_modules and not python_modules.startswith('/'):
            return os.path.join(self.base_path, python_modules)
        return python_modules

    @property
    def tracking_helper_path(self) -> str:
        paths_config = self._config.get('file_paths', self._config.get('paths', {}))
        tracking_helper = paths_config.get('tracking_helper', '')
        if tracking_helper and not tracking_helper.startswith('/'):
            return os.path.join(self.base_path, tracking_helper)
        return tracking_helper

    def get_request_path(self, request_id: str) -> str:
        """Get path for a specific request."""
        return os.path.join(self.request_processing_path, request_id)

    def get_files_path(self, request_id: str) -> str:
        """Get FILES path for a specific request."""
        return os.path.join(self.get_request_path(request_id), 'FILES')

    def get_logs_path(self, request_id: str) -> str:
        """Get LOGS path for a specific request."""
        return os.path.join(self.get_request_path(request_id), 'LOGS')

    def get_config_properties_path(self, request_id: str) -> str:
        """Get config.properties path for a specific request."""
        return os.path.join(self.get_request_path(request_id), 'ETC', 'config.properties')

    # ==================== Indexes ====================

    def get_index_name(self, index_type: str, request_id: str, decile: str) -> str:
        """
        Generate index name from template.

        Args:
            index_type: 'email', 'seg_subseg', or 'md5'
            request_id: Request ID
            decile: Decile number

        Returns:
            Formatted index name
        """
        template = self._config['indexes'].get(index_type, f"idx_{{request_id}}_{{decile}}_{index_type}")
        return template.format(request_id=request_id, decile=decile)

    # ==================== Query Templates ====================

    def get_request_details_query(self, request_id: str) -> str:
        """Get formatted request details query."""
        template = self._config['queries']['request_details']
        return template.format(
            requests_table=self.requests_table,
            clients_table=self.clients_table,
            request_id=request_id
        )

    def get_update_status_query(self, request_id: str, description: str) -> str:
        """Get formatted update status query."""
        template = self._config['queries']['update_status']
        return template.format(
            requests_table=self.requests_table,
            description=description,
            request_id=request_id
        )

    def get_update_desc_query(self, request_id: str, description: str) -> str:
        """Get formatted update description query."""
        template = self._config['queries']['update_desc']
        return template.format(
            requests_table=self.requests_table,
            description=description,
            request_id=request_id
        )

    def get_update_qa_count_query(self, request_id: str, count: int) -> str:
        """Get formatted update QA count query."""
        template = self._config['queries']['update_qa_count']
        return template.format(
            qa_table=self.qa_stats_table,
            count=count,
            request_id=request_id
        )


# Singleton instance for easy import
_config_instance = None


def get_config() -> ConfigLoader:
    """Get singleton ConfigLoader instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


# Convenience functions for direct access
def get_table(key: str) -> str:
    """Quick access to table names."""
    return get_config().get_table(key)


def get_db_connection_params() -> Dict[str, Any]:
    """Get database connection parameters as dict."""
    cfg = get_config()
    return {
        'host': cfg.db_host,
        'port': cfg.db_port,
        'database': cfg.db_name,
        'user': cfg.db_user
    }
