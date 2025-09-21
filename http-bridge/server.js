#!/usr/bin/env node

/**
 * Crypto Trading MCP HTTP Bridge Server
 *
 * Provides HTTP and WebSocket endpoints for n8n MCP Client integration
 * Bridges to Python MCP servers via STDIO transport
 *
 * Endpoints:
 * - POST /mcp - JSON-RPC 2.0 endpoint for n8n
 * - GET /health - Health check
 * - GET /metrics - Performance metrics
 * - WS /ws - WebSocket transport (optional)
 */

import express from 'express';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import pino from 'pino';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

import { JsonRpcHandler } from './json-rpc-handler.js';
import { McpBridge } from './mcp-bridge.js';
import { ServerConfig } from './config.js';

// Load environment variables
dotenv.config({ path: join(dirname(fileURLToPath(import.meta.url)), '..', '.env') });

// Initialize logger
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname'
    }
  }
});

class CryptoTradingMcpServer {
  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.wss = new WebSocketServer({ server: this.server });
    this.config = new ServerConfig();
    this.jsonRpcHandler = new JsonRpcHandler(logger);
    this.mcpBridge = new McpBridge(logger);
    this.isShuttingDown = false;

    // Performance metrics
    this.metrics = {
      startTime: Date.now(),
      requests: 0,
      errors: 0,
      wsConnections: 0
    };
  }

  setupMiddleware() {
    // Security headers
    this.app.use(helmet({
      contentSecurityPolicy: false, // Allow for development
      crossOriginEmbedderPolicy: false
    }));

    // Compression
    this.app.use(compression());

    // CORS for n8n integration
    const corsConfig = this.config.getCorsConfig();
    if (corsConfig) {
      this.app.use(cors(corsConfig));
    }

    // Rate limiting
    const limiter = rateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 1000, // 1000 requests per minute
      message: {
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Rate limit exceeded'
        },
        id: null
      },
      standardHeaders: true,
      legacyHeaders: false
    });
    this.app.use('/mcp', limiter);

    // Request parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      this.metrics.requests++;
      logger.info({
        method: req.method,
        url: req.url,
        userAgent: req.get('User-Agent'),
        ip: req.ip
      }, 'Incoming request');
      next();
    });
  }

  setupRoutes() {
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: Date.now() - this.metrics.startTime,
        version: process.env.npm_package_version || '1.0.0',
        node: process.version,
        memory: process.memoryUsage(),
        mcpServers: this.mcpBridge.getServerStatus()
      };

      res.json(health);
    });

    // Metrics endpoint
    this.app.get('/metrics', (req, res) => {
      const metrics = {
        ...this.metrics,
        uptime: Date.now() - this.metrics.startTime,
        memory: process.memoryUsage(),
        mcpServers: this.mcpBridge.getServerStats()
      };

      res.json(metrics);
    });

    // Main MCP JSON-RPC 2.0 endpoint for n8n
    this.app.post('/mcp', async (req, res) => {
      try {
        const jsonRpcRequest = req.body;

        // Validate JSON-RPC 2.0 format
        if (!this.jsonRpcHandler.isValidRequest(jsonRpcRequest)) {
          const errorResponse = this.jsonRpcHandler.createErrorResponse(
            -32600,
            'Invalid Request',
            'Request must be valid JSON-RPC 2.0 format',
            jsonRpcRequest.id || null
          );
          return res.status(400).json(errorResponse);
        }

        // Route request to appropriate MCP server
        const response = await this.jsonRpcHandler.handleRequest(
          jsonRpcRequest,
          this.mcpBridge
        );

        res.json(response);

      } catch (error) {
        this.metrics.errors++;
        logger.error({ error: error.message, stack: error.stack }, 'MCP request error');

        const errorResponse = this.jsonRpcHandler.createErrorResponse(
          -32603,
          'Internal error',
          error.message,
          req.body?.id || null
        );

        res.status(500).json(errorResponse);
      }
    });

    // WebSocket endpoint for streaming (optional)
    this.app.get('/ws', (req, res) => {
      res.status(200).send('WebSocket endpoint available at ws://localhost:' + this.config.port + '/ws');
    });

    // Handle 404
    this.app.use('*', (req, res) => {
      res.status(404).json({
        jsonrpc: '2.0',
        error: {
          code: -32601,
          message: 'Method not found',
          data: `Endpoint ${req.originalUrl} not found. Available: /mcp, /health, /metrics, /ws`
        },
        id: null
      });
    });

    // Global error handler
    this.app.use((error, req, res, next) => {
      this.metrics.errors++;
      logger.error({ error: error.message, stack: error.stack }, 'Express error');

      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal error',
          data: error.message
        },
        id: null
      });
    });
  }

  setupWebSocket() {
    this.wss.on('connection', (ws, req) => {
      this.metrics.wsConnections++;
      logger.info({ ip: req.socket.remoteAddress }, 'WebSocket connection established');

      ws.on('message', async (data) => {
        try {
          const message = JSON.parse(data.toString());

          if (this.jsonRpcHandler.isValidRequest(message)) {
            const response = await this.jsonRpcHandler.handleRequest(message, this.mcpBridge);
            ws.send(JSON.stringify(response));
          } else {
            const errorResponse = this.jsonRpcHandler.createErrorResponse(
              -32600,
              'Invalid Request',
              'WebSocket message must be valid JSON-RPC 2.0',
              message.id || null
            );
            ws.send(JSON.stringify(errorResponse));
          }
        } catch (error) {
          this.metrics.errors++;
          logger.error({ error: error.message }, 'WebSocket message error');

          const errorResponse = this.jsonRpcHandler.createErrorResponse(
            -32700,
            'Parse error',
            'Invalid JSON',
            null
          );
          ws.send(JSON.stringify(errorResponse));
        }
      });

      ws.on('close', () => {
        this.metrics.wsConnections--;
        logger.info('WebSocket connection closed');
      });

      ws.on('error', (error) => {
        this.metrics.errors++;
        logger.error({ error: error.message }, 'WebSocket error');
      });
    });
  }

  async start() {
    try {
      // Initialize MCP bridge to Python servers
      await this.mcpBridge.initialize();

      // Setup Express middleware and routes
      this.setupMiddleware();
      this.setupRoutes();
      this.setupWebSocket();

      // Start HTTP server
      const port = this.config.port;
      await new Promise((resolve, reject) => {
        this.server.listen(port, this.config.host, (error) => {
          if (error) reject(error);
          else resolve();
        });
      });

      logger.info({
        port,
        host: this.config.host,
        env: process.env.NODE_ENV || 'development'
      }, 'Crypto Trading MCP HTTP Bridge started');

      logger.info(`📊 MCP Endpoint: http://${this.config.host}:${port}/mcp`);
      logger.info(`🔍 Health Check: http://${this.config.host}:${port}/health`);
      logger.info(`📈 Metrics: http://${this.config.host}:${port}/metrics`);
      logger.info(`🔌 WebSocket: ws://${this.config.host}:${port}/ws`);

    } catch (error) {
      logger.error({ error: error.message, stack: error.stack }, 'Failed to start server');
      process.exit(1);
    }
  }

  async shutdown() {
    if (this.isShuttingDown) return;
    this.isShuttingDown = true;

    logger.info('Shutting down Crypto Trading MCP HTTP Bridge...');

    try {
      // Close WebSocket connections
      this.wss.clients.forEach(ws => ws.close());

      // Shutdown MCP bridge
      await this.mcpBridge.shutdown();

      // Close HTTP server
      await new Promise((resolve) => {
        this.server.close(resolve);
      });

      logger.info('Server shutdown complete');
      process.exit(0);
    } catch (error) {
      logger.error({ error: error.message }, 'Error during shutdown');
      process.exit(1);
    }
  }
}

// Initialize and start server
const mcpServer = new CryptoTradingMcpServer();

// Graceful shutdown handlers
process.on('SIGTERM', () => mcpServer.shutdown());
process.on('SIGINT', () => mcpServer.shutdown());
process.on('uncaughtException', (error) => {
  logger.fatal({ error: error.message, stack: error.stack }, 'Uncaught exception');
  mcpServer.shutdown();
});
process.on('unhandledRejection', (reason, promise) => {
  logger.fatal({ reason, promise }, 'Unhandled rejection');
  mcpServer.shutdown();
});

// Start the server
mcpServer.start().catch(error => {
  logger.fatal({ error: error.message, stack: error.stack }, 'Failed to start server');
  process.exit(1);
});