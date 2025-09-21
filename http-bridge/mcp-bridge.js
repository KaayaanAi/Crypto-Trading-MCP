/**
 * MCP Bridge
 *
 * Bridges HTTP JSON-RPC requests to Python MCP servers via STDIO transport
 * Manages lifecycle, connection pooling, and error handling for all MCP servers
 */

import { spawn } from 'child_process';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { EventEmitter } from 'events';

const __dirname = dirname(fileURLToPath(import.meta.url));

export class McpBridge extends EventEmitter {
  constructor(logger) {
    super();
    this.logger = logger;
    this.servers = new Map();
    this.isInitialized = false;

    // Server configurations
    this.serverConfigs = {
      binance: {
        name: 'binance-mcp',
        script: join(__dirname, '..', 'servers', 'binance-mcp', 'main.py'),
        description: 'Binance exchange integration for market data and trading',
        timeout: 30000
      },
      technical: {
        name: 'crypto-technical-mcp',
        script: join(__dirname, '..', 'servers', 'crypto-technical-mcp', 'main.py'),
        description: 'Technical analysis indicators and pattern detection',
        timeout: 15000
      },
      news: {
        name: 'crypto-news-mcp',
        script: join(__dirname, '..', 'servers', 'crypto-news-mcp', 'main.py'),
        description: 'Crypto news aggregation and sentiment analysis',
        timeout: 10000
      },
      social: {
        name: 'crypto-social-mcp',
        script: join(__dirname, '..', 'servers', 'crypto-social-mcp', 'main.py'),
        description: 'Social media sentiment and Fear & Greed index',
        timeout: 10000
      },
      risk: {
        name: 'crypto-risk-mcp',
        script: join(__dirname, '..', 'servers', 'crypto-risk-mcp', 'main.py'),
        description: 'Risk management and position sizing calculations',
        timeout: 5000
      },
      ai: {
        name: 'crypto-ai-mcp',
        script: join(__dirname, '..', 'servers', 'crypto-ai-mcp', 'main.py'),
        description: 'AI-powered market analysis using Ollama',
        timeout: 45000
      }
    };

    // Request counter for IDs
    this.requestId = 0;
  }

  /**
   * Initialize all MCP servers
   */
  async initialize() {
    if (this.isInitialized) {
      return;
    }

    this.logger.info('Initializing MCP bridge...');

    const initPromises = Object.entries(this.serverConfigs).map(
      ([serverName, config]) => this.initializeServer(serverName, config)
    );

    try {
      await Promise.all(initPromises);
      this.isInitialized = true;
      this.logger.info('All MCP servers initialized successfully');
    } catch (error) {
      this.logger.error({ error: error.message }, 'Failed to initialize MCP servers');
      throw new Error(`MCP bridge initialization failed: ${error.message}`);
    }
  }

  /**
   * Initialize a single MCP server
   */
  async initializeServer(serverName, config) {
    try {
      this.logger.info({ serverName, script: config.script }, 'Starting MCP server');

      const childProcess = spawn('python3', [config.script], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env }
      });

      const server = {
        name: serverName,
        process: childProcess,
        config,
        isReady: false,
        pendingRequests: new Map(),
        tools: [],
        resources: [],
        prompts: []
      };

      // Handle server stdout (responses)
      childProcess.stdout.on('data', (data) => {
        this.handleServerResponse(serverName, data);
      });

      // Handle server stderr (errors/logs)
      childProcess.stderr.on('data', (data) => {
        this.logger.warn({ serverName, stderr: data.toString() }, 'Server stderr');
      });

      // Handle server exit
      childProcess.on('exit', (code, signal) => {
        this.logger.error({ serverName, code, signal }, 'MCP server exited');
        server.isReady = false;
        this.emit('serverExit', serverName, code, signal);
      });

      // Handle server errors
      childProcess.on('error', (error) => {
        this.logger.error({ serverName, error: error.message }, 'MCP server error');
        server.isReady = false;
        this.emit('serverError', serverName, error);
      });

      this.servers.set(serverName, server);

      // Initialize server with MCP handshake
      await this.initializeServerMcp(serverName);

      // Get available tools, resources, and prompts
      await this.loadServerCapabilities(serverName);

      server.isReady = true;
      this.logger.info({ serverName, toolCount: server.tools.length }, 'MCP server ready');

    } catch (error) {
      this.logger.error({ serverName, error: error.message }, 'Failed to initialize server');
      throw error;
    }
  }

  /**
   * Send MCP initialize request to server
   */
  async initializeServerMcp(serverName) {
    const initRequest = {
      jsonrpc: '2.0',
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {
          roots: { listChanged: false },
          sampling: {}
        },
        clientInfo: {
          name: 'crypto-trading-mcp-bridge',
          version: '1.0.0'
        }
      },
      id: this.getNextRequestId()
    };

    const response = await this.sendRequest(serverName, initRequest);

    if (response.error) {
      throw new Error(`Server initialization failed: ${response.error.message}`);
    }

    return response.result;
  }

  /**
   * Load server capabilities (tools, resources, prompts)
   */
  async loadServerCapabilities(serverName) {
    const server = this.servers.get(serverName);
    if (!server) return;

    try {
      // Load tools
      const toolsResponse = await this.sendRequest(serverName, {
        jsonrpc: '2.0',
        method: 'tools/list',
        id: this.getNextRequestId()
      });

      if (toolsResponse.result?.tools) {
        server.tools = toolsResponse.result.tools.map(tool => ({
          ...tool,
          serverName
        }));
      }

      // Load resources (optional)
      try {
        const resourcesResponse = await this.sendRequest(serverName, {
          jsonrpc: '2.0',
          method: 'resources/list',
          id: this.getNextRequestId()
        });

        if (resourcesResponse.result?.resources) {
          server.resources = resourcesResponse.result.resources.map(resource => ({
            ...resource,
            serverName
          }));
        }
      } catch (error) {
        // Resources are optional
        this.logger.debug({ serverName }, 'Server does not support resources');
      }

      // Load prompts (optional)
      try {
        const promptsResponse = await this.sendRequest(serverName, {
          jsonrpc: '2.0',
          method: 'prompts/list',
          id: this.getNextRequestId()
        });

        if (promptsResponse.result?.prompts) {
          server.prompts = promptsResponse.result.prompts.map(prompt => ({
            ...prompt,
            serverName
          }));
        }
      } catch (error) {
        // Prompts are optional
        this.logger.debug({ serverName }, 'Server does not support prompts');
      }

    } catch (error) {
      this.logger.error({ serverName, error: error.message }, 'Failed to load server capabilities');
    }
  }

  /**
   * Handle response data from server
   */
  handleServerResponse(serverName, data) {
    const server = this.servers.get(serverName);
    if (!server) return;

    const dataStr = data.toString();
    const lines = dataStr.split('\n').filter(line => line.trim());

    for (const line of lines) {
      try {
        const response = JSON.parse(line);

        if (response.id && server.pendingRequests.has(response.id)) {
          const { resolve, reject, timeout } = server.pendingRequests.get(response.id);

          clearTimeout(timeout);
          server.pendingRequests.delete(response.id);

          if (response.error) {
            reject(new Error(response.error.message || 'Server error'));
          } else {
            resolve(response);
          }
        }

      } catch (error) {
        this.logger.debug({ serverName, line }, 'Non-JSON server output');
      }
    }
  }

  /**
   * Send request to specific MCP server
   */
  async sendRequest(serverName, request) {
    const server = this.servers.get(serverName);
    if (!server) {
      throw new Error(`Server ${serverName} not found`);
    }

    if (!server.isReady && request.method !== 'initialize') {
      throw new Error(`Server ${serverName} not ready`);
    }

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        server.pendingRequests.delete(request.id);
        reject(new Error(`Request timeout for server ${serverName}`));
      }, server.config.timeout);

      server.pendingRequests.set(request.id, { resolve, reject, timeout });

      const requestStr = JSON.stringify(request) + '\n';
      server.process.stdin.write(requestStr);

      this.logger.debug({ serverName, method: request.method, id: request.id }, 'Sent request');
    });
  }

  /**
   * Call a tool on a specific server
   */
  async callTool(serverName, toolName, arguments_) {
    const request = {
      jsonrpc: '2.0',
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: arguments_
      },
      id: this.getNextRequestId()
    };

    const response = await this.sendRequest(serverName, request);

    if (response.error) {
      throw new Error(response.error.message);
    }

    return response.result;
  }

  /**
   * Get all tools from all servers
   */
  async getAllTools() {
    const allTools = [];

    for (const [serverName, server] of this.servers) {
      if (server.isReady) {
        allTools.push(...server.tools);
      }
    }

    return allTools;
  }

  /**
   * Get all resources from all servers
   */
  async getAllResources() {
    const allResources = [];

    for (const [serverName, server] of this.servers) {
      if (server.isReady) {
        allResources.push(...server.resources);
      }
    }

    return allResources;
  }

  /**
   * Get all prompts from all servers
   */
  async getAllPrompts() {
    const allPrompts = [];

    for (const [serverName, server] of this.servers) {
      if (server.isReady) {
        allPrompts.push(...server.prompts);
      }
    }

    return allPrompts;
  }

  /**
   * Read a resource from a server
   */
  async readResource(uri) {
    // Extract server name from URI (format: server://resource-path)
    const [protocol, ...pathParts] = uri.split('://');
    const serverName = protocol;
    const resourcePath = pathParts.join('://');

    const request = {
      jsonrpc: '2.0',
      method: 'resources/read',
      params: { uri: resourcePath },
      id: this.getNextRequestId()
    };

    const response = await this.sendRequest(serverName, request);

    if (response.error) {
      throw new Error(response.error.message);
    }

    return response.result.contents[0];
  }

  /**
   * Get a prompt from a server
   */
  async getPrompt(name, arguments_) {
    // Find which server has this prompt
    let targetServer = null;
    for (const [serverName, server] of this.servers) {
      if (server.prompts.some(p => p.name === name)) {
        targetServer = serverName;
        break;
      }
    }

    if (!targetServer) {
      throw new Error(`Prompt ${name} not found in any server`);
    }

    const request = {
      jsonrpc: '2.0',
      method: 'prompts/get',
      params: { name, arguments: arguments_ },
      id: this.getNextRequestId()
    };

    const response = await this.sendRequest(targetServer, request);

    if (response.error) {
      throw new Error(response.error.message);
    }

    return response.result;
  }

  /**
   * Get server status for health checks
   */
  getServerStatus() {
    const status = {};

    for (const [serverName, server] of this.servers) {
      status[serverName] = {
        ready: server.isReady,
        pid: server.process.pid,
        toolCount: server.tools.length,
        resourceCount: server.resources.length,
        promptCount: server.prompts.length
      };
    }

    return status;
  }

  /**
   * Get server statistics
   */
  getServerStats() {
    const stats = {};

    for (const [serverName, server] of this.servers) {
      stats[serverName] = {
        pendingRequests: server.pendingRequests.size,
        isReady: server.isReady,
        capabilities: {
          tools: server.tools.length,
          resources: server.resources.length,
          prompts: server.prompts.length
        }
      };
    }

    return stats;
  }

  /**
   * Shutdown all servers
   */
  async shutdown() {
    this.logger.info('Shutting down MCP bridge...');

    const shutdownPromises = [];

    for (const [serverName, server] of this.servers) {
      shutdownPromises.push(this.shutdownServer(serverName, server));
    }

    await Promise.allSettled(shutdownPromises);
    this.servers.clear();
    this.isInitialized = false;

    this.logger.info('MCP bridge shutdown complete');
  }

  /**
   * Shutdown a single server
   */
  async shutdownServer(serverName, server) {
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        this.logger.warn({ serverName }, 'Force killing server');
        server.process.kill('SIGKILL');
        resolve();
      }, 5000);

      server.process.on('exit', () => {
        clearTimeout(timeout);
        resolve();
      });

      this.logger.info({ serverName }, 'Shutting down server');
      server.process.kill('SIGTERM');
    });
  }

  /**
   * Get next request ID
   */
  getNextRequestId() {
    return ++this.requestId;
  }
}