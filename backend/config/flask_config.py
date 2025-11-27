"""
Flask configuration for Campaign Attribution Management (CAM)
Professional configuration with enterprise-grade settings
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""

    # Basic Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cam-dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False

    # Database configuration (SQLAlchemy - for future use)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://datateam:Datat3amSU!@zds-prod-pgdb01-01.bo3.e-dialog.com:5432/apt_tool_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'cam-jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # API configuration
    API_VERSION = '1.0'
    API_TITLE = 'Campaign Attribution Management API'
    API_DESCRIPTION = 'Professional API for Campaign Attribution Processing'

    # CORS configuration
    CORS_ORIGINS = [
        'http://localhost:3009',
        'http://127.0.0.1:3009',
        'http://localhost:3000',
        'http://127.0.0.1:3000'
    ]

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'

    # Pagination
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 100

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

    # Enhanced security for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration class based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, config_map['default'])
