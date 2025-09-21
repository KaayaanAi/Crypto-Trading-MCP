/**
 * Server Configuration
 *
 * Centralized configuration management for the MCP HTTP bridge
 * Handles environment variables, defaults, and validation
 */

export class ServerConfig {
  constructor() {
    this.loadConfiguration();
    this.validateConfiguration();
  }

  loadConfiguration() {
    // Server settings
    this.host = process.env.MCP_HOST || '0.0.0.0';
    this.port = parseInt(process.env.MCP_PORT || '8080', 10);

    // Environment
    this.nodeEnv = process.env.NODE_ENV || 'development';
    this.isDevelopment = this.nodeEnv === 'development';
    this.isProduction = this.nodeEnv === 'production';

    // Logging
    this.logLevel = process.env.LOG_LEVEL || (this.isDevelopment ? 'debug' : 'info');

    // Rate limiting
    this.rateLimitWindow = parseInt(process.env.RATE_LIMIT_WINDOW || '60000', 10); // 1 minute
    this.rateLimitMax = parseInt(process.env.RATE_LIMIT_MAX || '1000', 10); // 1000 requests

    // Request timeouts
    this.requestTimeout = parseInt(process.env.REQUEST_TIMEOUT || '30000', 10); // 30 seconds
    this.healthCheckTimeout = parseInt(process.env.HEALTH_CHECK_TIMEOUT || '5000', 10); // 5 seconds

    // Security
    this.enableCors = process.env.ENABLE_CORS !== 'false';
    this.enableHelmet = process.env.ENABLE_HELMET !== 'false';
    this.enableCompression = process.env.ENABLE_COMPRESSION !== 'false';

    // WebSocket
    this.enableWebSocket = process.env.ENABLE_WEBSOCKET !== 'false';
    this.maxWebSocketConnections = parseInt(process.env.MAX_WS_CONNECTIONS || '100', 10);

    // MCP server settings
    this.mcpServerTimeout = parseInt(process.env.MCP_SERVER_TIMEOUT || '30000', 10);
    this.mcpServerRetries = parseInt(process.env.MCP_SERVER_RETRIES || '3', 10);

    // Python interpreter
    this.pythonPath = process.env.PYTHON_PATH || 'python3';

    // Monitoring
    this.enableMetrics = process.env.ENABLE_METRICS !== 'false';
    this.metricsPort = parseInt(process.env.METRICS_PORT || '9090', 10);
  }

  validateConfiguration() {
    const errors = [];

    // Validate port
    if (this.port < 1 || this.port > 65535) {
      errors.push(`Invalid port: ${this.port}. Must be between 1 and 65535.`);
    }

    // Validate timeouts
    if (this.requestTimeout < 1000) {
      errors.push(`Request timeout too low: ${this.requestTimeout}ms. Minimum is 1000ms.`);
    }

    if (this.mcpServerTimeout < 5000) {
      errors.push(`MCP server timeout too low: ${this.mcpServerTimeout}ms. Minimum is 5000ms.`);
    }

    // Validate rate limiting
    if (this.rateLimitMax < 1) {
      errors.push(`Rate limit max too low: ${this.rateLimitMax}. Must be at least 1.`);
    }

    if (this.rateLimitWindow < 1000) {
      errors.push(`Rate limit window too low: ${this.rateLimitWindow}ms. Minimum is 1000ms.`);
    }

    // Validate log level
    const validLogLevels = ['fatal', 'error', 'warn', 'info', 'debug', 'trace'];
    if (!validLogLevels.includes(this.logLevel)) {
      errors.push(`Invalid log level: ${this.logLevel}. Must be one of: ${validLogLevels.join(', ')}`);
    }

    if (errors.length > 0) {
      throw new Error(`Configuration validation failed:\n${errors.join('\n')}`);
    }
  }

  /**
   * Get configuration summary for logging
   */
  getSummary() {
    return {
      server: {
        host: this.host,
        port: this.port,
        environment: this.nodeEnv
      },
      features: {
        cors: this.enableCors,
        helmet: this.enableHelmet,
        compression: this.enableCompression,
        websocket: this.enableWebSocket,
        metrics: this.enableMetrics
      },
      timeouts: {
        request: this.requestTimeout,
        mcpServer: this.mcpServerTimeout,
        healthCheck: this.healthCheckTimeout
      },
      rateLimiting: {
        window: this.rateLimitWindow,
        max: this.rateLimitMax
      },
      logging: {
        level: this.logLevel
      }
    };
  }

  /**
   * Check if running in development mode
   */
  isDev() {
    return this.isDevelopment;
  }

  /**
   * Check if running in production mode
   */
  isProd() {
    return this.isProduction;
  }

  /**
   * Get CORS configuration
   */
  getCorsConfig() {
    if (!this.enableCors) {
      return null;
    }

    return {
      origin: this.isDevelopment ? true : (process.env.CORS_ORIGINS?.split(',') || true),
      credentials: true,
      methods: ['GET', 'POST', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
      maxAge: 86400 // 24 hours
    };
  }

  /**
   * Get rate limiting configuration
   */
  getRateLimitConfig() {
    return {
      windowMs: this.rateLimitWindow,
      max: this.rateLimitMax,
      message: {
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Rate limit exceeded',
          data: `Maximum ${this.rateLimitMax} requests per ${this.rateLimitWindow / 1000} seconds`
        },
        id: null
      },
      standardHeaders: true,
      legacyHeaders: false,
      // Skip rate limiting for health checks
      skip: (req) => req.path === '/health'
    };
  }

  /**
   * Get WebSocket configuration
   */
  getWebSocketConfig() {
    return {
      enabled: this.enableWebSocket,
      maxConnections: this.maxWebSocketConnections,
      pingInterval: 30000, // 30 seconds
      pongTimeout: 5000   // 5 seconds
    };
  }

  /**
   * Get server startup banner
   */
  getStartupBanner() {
    return `
┌─────────────────────────────────────────────────────────────┐
│                 Crypto Trading MCP Bridge                  │
│                     HTTP Server v1.0.0                     │
├─────────────────────────────────────────────────────────────┤
│ Environment: ${this.nodeEnv.padEnd(10)} │ Port: ${this.port.toString().padStart(5)} │ Host: ${this.host.padEnd(9)} │
│ Log Level:   ${this.logLevel.padEnd(10)} │ CORS: ${(this.enableCors ? 'ON' : 'OFF').padStart(5)} │ WS:   ${(this.enableWebSocket ? 'ON' : 'OFF').padEnd(9)} │
└─────────────────────────────────────────────────────────────┘
    `.trim();
  }
}