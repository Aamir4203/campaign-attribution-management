// Database Configuration
export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  tables: {
    clients: string;
    requests: string;
    qa_stats: string;
    users: string;
    postback_prefix: string;
  };
  pools: {
    min_size: number;
    max_size: number;
    timeout: number;
  };
}

// Application Constants
export interface AppConstants {
  pagination: {
    defaultPageSize: number;
    maxPageSize: number;
  };
  requests: {
    maxRetries: number;
    timeoutMs: number;
    validStatuses: string[];
  };
  files: {
    maxUploadSize: number;
    allowedTypes: string[];
    uploadPath: string;
  };
  modules: Record<number, string>;
  api: {
    baseUrl: string;
    timeout: number;
    retries: number;
  };
}

// ZETA Theme Configuration
export interface ThemeConfig {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    gradients: {
      primary: string;
      secondary: string;
      accent: string;
    };
  };
  spacing: Record<string, string>;
  typography: Record<string, any>;
  components: Record<string, any>;
}

// Security Configuration
export interface SecurityConfig {
  jwt: {
    secret: string;
    expiration: string;
    issuer: string;
  };
  cors: {
    origins: string[];
    methods: string[];
    headers: string[];
  };
  rateLimit: {
    requests: number;
    window: number;
  };
}

// Complete Application Configuration
export interface AppConfig {
  database: DatabaseConfig;
  constants: AppConstants;
  theme: ThemeConfig;
  security: SecurityConfig;
  environment: 'development' | 'staging' | 'production';
  debug: boolean;
}
