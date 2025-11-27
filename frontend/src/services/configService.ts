/**
 * Configuration Service for CAM Frontend
 * Loads configuration from environment and provides typed access
 */

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
}

export interface ThemeConfig {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
  };
  gradients: {
    client: string;
    date: string;
    file: string;
    report: string;
    query: string;
    submit: string;
  };
}

export interface AppConfig {
  api: ApiConfig;
  theme: ThemeConfig;
  environment: string;
  debug: boolean;
}

class ConfigService {
  private config: AppConfig;

  constructor() {
    this.config = this.loadConfig();
  }

  private loadConfig(): AppConfig {
    // Default configuration
    const defaultConfig: AppConfig = {
      api: {
        baseUrl: this.getEnvValue('VITE_API_BASE_URL') || 'http://localhost:5000',
        timeout: parseInt(this.getEnvValue('VITE_API_TIMEOUT') || '30000'),
        retries: parseInt(this.getEnvValue('VITE_API_RETRIES') || '3'),
      },
      theme: {
        colors: {
          primary: '#1E40AF',
          secondary: '#7C3AED',
          accent: '#F97316',
        },
        gradients: {
          client: 'from-blue-100 to-indigo-100',
          date: 'from-orange-100 to-red-100',
          file: 'from-emerald-100 to-teal-100',
          report: 'from-amber-100 to-yellow-100',
          query: 'from-rose-100 to-pink-100',
          submit: 'from-blue-600 to-purple-600',
        },
      },
      environment: this.getEnvValue('VITE_ENVIRONMENT') || 'development',
      debug: this.getEnvValue('VITE_DEBUG') === 'true' || false,
    };

    // Log configuration in debug mode
    if (defaultConfig.debug) {
      console.log('🔧 CAM Configuration loaded:', defaultConfig);
    }

    return defaultConfig;
  }

  private getEnvValue(key: string): string | undefined {
    // Check for Vite environment variables
    if (typeof import.meta !== 'undefined' && import.meta.env) {
      return import.meta.env[key];
    }

    // Check for Node.js environment variables
    if (typeof process !== 'undefined' && process.env) {
      return process.env[key];
    }

    return undefined;
  }

  /**
   * Get complete configuration
   */
  getConfig(): AppConfig {
    return this.config;
  }

  /**
   * Get API configuration
   */
  getApiConfig(): ApiConfig {
    return this.config.api;
  }

  /**
   * Get API base URL
   */
  getApiBaseUrl(): string {
    return this.config.api.baseUrl;
  }

  /**
   * Get API timeout
   */
  getApiTimeout(): number {
    return this.config.api.timeout;
  }

  /**
   * Get theme configuration
   */
  getThemeConfig(): ThemeConfig {
    return this.config.theme;
  }

  /**
   * Get gradient class for specific section
   */
  getSectionGradient(section: keyof ThemeConfig['gradients']): string {
    return this.config.theme.gradients[section];
  }

  /**
   * Get primary color
   */
  getPrimaryColor(): string {
    return this.config.theme.colors.primary;
  }

  /**
   * Check if debug mode is enabled
   */
  isDebug(): boolean {
    return this.config.debug;
  }

  /**
   * Get environment
   */
  getEnvironment(): string {
    return this.config.environment;
  }

  /**
   * Check if development mode
   */
  isDevelopment(): boolean {
    return this.config.environment === 'development';
  }

  /**
   * Check if production mode
   */
  isProduction(): boolean {
    return this.config.environment === 'production';
  }

  /**
   * Get full API endpoint URL
   */
  getApiUrl(endpoint: string): string {
    const baseUrl = this.getApiBaseUrl();
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${baseUrl}${cleanEndpoint}`;
  }

  /**
   * Log configuration info (if debug is enabled)
   */
  logConfig(): void {
    if (this.isDebug()) {
      console.group('🔧 CAM Configuration');
      console.log('Environment:', this.getEnvironment());
      console.log('Debug Mode:', this.isDebug());
      console.log('API Base URL:', this.getApiBaseUrl());
      console.log('API Timeout:', this.getApiTimeout());
      console.log('Theme Colors:', this.config.theme.colors);
      console.groupEnd();
    }
  }

  /**
   * Update configuration at runtime (for testing)
   */
  updateConfig(updates: Partial<AppConfig>): void {
    this.config = {
      ...this.config,
      ...updates,
      api: { ...this.config.api, ...(updates.api || {}) },
      theme: {
        ...this.config.theme,
        ...(updates.theme || {}),
        colors: { ...this.config.theme.colors, ...(updates.theme?.colors || {}) },
        gradients: { ...this.config.theme.gradients, ...(updates.theme?.gradients || {}) },
      },
    };

    if (this.isDebug()) {
      console.log('🔧 Configuration updated:', this.config);
    }
  }
}

// Create singleton instance
const configService = new ConfigService();

// Log configuration on initialization
configService.logConfig();

export default configService;
