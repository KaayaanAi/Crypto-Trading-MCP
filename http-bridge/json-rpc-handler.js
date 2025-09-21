/**
 * JSON-RPC 2.0 Handler
 *
 * Implements strict JSON-RPC 2.0 specification compliance for MCP protocol
 * Handles request validation, method routing, and response formatting
 */

export class JsonRpcHandler {
  constructor(logger) {
    this.logger = logger;

    // Standard JSON-RPC 2.0 error codes
    this.ERROR_CODES = {
      PARSE_ERROR: -32700,
      INVALID_REQUEST: -32600,
      METHOD_NOT_FOUND: -32601,
      INVALID_PARAMS: -32602,
      INTERNAL_ERROR: -32603,
      // MCP-specific error codes (-32000 to -32099)
      MCP_SERVER_ERROR: -32000,
      MCP_TIMEOUT_ERROR: -32001,
      MCP_RATE_LIMIT_ERROR: -32002,
      MCP_BRIDGE_ERROR: -32003
    };

    // Supported MCP methods
    this.MCP_METHODS = {
      INITIALIZE: 'initialize',
      TOOLS_LIST: 'tools/list',
      TOOLS_CALL: 'tools/call',
      RESOURCES_LIST: 'resources/list',
      RESOURCES_READ: 'resources/read',
      PROMPTS_LIST: 'prompts/list',
      PROMPTS_GET: 'prompts/get'
    };

    // Server routing table (maps tools to servers)
    this.SERVER_ROUTES = {
      // Binance MCP Server
      'get_ticker_price': 'binance',
      'get_order_book': 'binance',
      'place_order': 'binance',
      'cancel_order': 'binance',
      'get_account_info': 'binance',
      'get_open_orders': 'binance',
      'track_whale_movements': 'binance',

      // Technical Analysis MCP Server
      'calculate_indicators': 'technical',
      'detect_patterns': 'technical',
      'find_support_resistance': 'technical',
      'multi_timeframe_analysis': 'technical',

      // News MCP Server
      'fetch_crypto_news': 'news',
      'analyze_news_sentiment': 'news',
      'get_regulatory_updates': 'news',

      // Social Sentiment MCP Server
      'get_social_sentiment': 'social',
      'track_social_mentions': 'social',
      'get_fear_greed_index': 'social',

      // Risk Management MCP Server
      'calculate_position_size': 'risk',
      'assess_portfolio_risk': 'risk',
      'generate_risk_alerts': 'risk',

      // AI Analysis MCP Server
      'analyze_market_context': 'ai',
      'generate_trading_signals': 'ai',
      'explain_market_decision': 'ai'
    };
  }

  /**
   * Validate JSON-RPC 2.0 request format
   */
  isValidRequest(request) {
    return !(!request || typeof request !== 'object' ||
      request.jsonrpc !== '2.0' ||
      !request.method || typeof request.method !== 'string' ||
      request.id === undefined ||
      (request.params !== undefined &&
        typeof request.params !== 'object' &&
        !Array.isArray(request.params)));
  }

  /**
   * Create JSON-RPC 2.0 compliant success response
   */
  createSuccessResponse(result, id) {
    return {
      jsonrpc: '2.0',
      result,
      id
    };
  }

  /**
   * Create JSON-RPC 2.0 compliant error response
   */
  createErrorResponse(code, message, data = null, id = null) {
    const error = { code, message };
    if (data !== null) {
      error.data = data;
    }

    return {
      jsonrpc: '2.0',
      error,
      id
    };
  }

  /**
   * Route tool calls to appropriate MCP server
   */
  getServerForTool(toolName) {
    return this.SERVER_ROUTES[toolName] || null;
  }

  /**
   * Handle JSON-RPC 2.0 request and route to MCP bridge
   */
  async handleRequest(request, mcpBridge) {
    const { method, params, id } = request;

    try {
      this.logger.info({ method, params, id }, 'Processing JSON-RPC request');

      switch (method) {
        case this.MCP_METHODS.INITIALIZE:
          return await this.handleInitialize(params, id, mcpBridge);

        case this.MCP_METHODS.TOOLS_LIST:
          return await this.handleToolsList(params, id, mcpBridge);

        case this.MCP_METHODS.TOOLS_CALL:
          return await this.handleToolsCall(params, id, mcpBridge);

        case this.MCP_METHODS.RESOURCES_LIST:
          return await this.handleResourcesList(params, id, mcpBridge);

        case this.MCP_METHODS.RESOURCES_READ:
          return await this.handleResourcesRead(params, id, mcpBridge);

        case this.MCP_METHODS.PROMPTS_LIST:
          return await this.handlePromptsList(params, id, mcpBridge);

        case this.MCP_METHODS.PROMPTS_GET:
          return await this.handlePromptsGet(params, id, mcpBridge);

        default:
          return this.createErrorResponse(
            this.ERROR_CODES.METHOD_NOT_FOUND,
            'Method not found',
            `Method '${method}' is not supported. Available methods: ${Object.values(this.MCP_METHODS).join(', ')}`,
            id
          );
      }

    } catch (error) {
      this.logger.error({ error: error.message, method, id }, 'Request handling error');

      return this.createErrorResponse(
        this.ERROR_CODES.INTERNAL_ERROR,
        'Internal error',
        error.message,
        id
      );
    }
  }

  /**
   * Handle MCP initialize method
   */
  async handleInitialize(params, id, mcpBridge) {
    try {
      await mcpBridge.initialize();

      const result = {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {},
          resources: {},
          prompts: {},
          logging: {}
        },
        serverInfo: {
          name: 'crypto-trading-mcp-bridge',
          version: '1.0.0'
        }
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_BRIDGE_ERROR,
        'Failed to initialize MCP bridge',
        error.message,
        id
      );
    }
  }

  /**
   * Handle tools/list method - aggregate from all servers
   */
  async handleToolsList(params, id, mcpBridge) {
    try {
      const allTools = await mcpBridge.getAllTools();

      const result = {
        tools: allTools
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Failed to list tools',
        error.message,
        id
      );
    }
  }

  /**
   * Handle tools/call method - route to specific server
   */
  async handleToolsCall(params, id, mcpBridge) {
    try {
      if (!params?.name) {
        return this.createErrorResponse(
          this.ERROR_CODES.INVALID_PARAMS,
          'Invalid params',
          'Tool name is required',
          id
        );
      }

      const { name: toolName, arguments: toolArgs = {} } = params;

      // Route to appropriate server
      const serverName = this.getServerForTool(toolName);
      if (!serverName) {
        return this.createErrorResponse(
          this.ERROR_CODES.METHOD_NOT_FOUND,
          'Tool not found',
          `Tool '${toolName}' is not available. Use tools/list to see available tools.`,
          id
        );
      }

      // Execute tool on specific server
      const result = await mcpBridge.callTool(serverName, toolName, toolArgs);

      return this.createSuccessResponse(result, id);

    } catch (error) {
      if (error.message.includes('timeout')) {
        return this.createErrorResponse(
          this.ERROR_CODES.MCP_TIMEOUT_ERROR,
          'Tool execution timeout',
          error.message,
          id
        );
      }

      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Tool execution failed',
        error.message,
        id
      );
    }
  }

  /**
   * Handle resources/list method
   */
  async handleResourcesList(params, id, mcpBridge) {
    try {
      const resources = await mcpBridge.getAllResources();

      const result = {
        resources
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Failed to list resources',
        error.message,
        id
      );
    }
  }

  /**
   * Handle resources/read method
   */
  async handleResourcesRead(params, id, mcpBridge) {
    try {
      if (!params?.uri) {
        return this.createErrorResponse(
          this.ERROR_CODES.INVALID_PARAMS,
          'Invalid params',
          'Resource URI is required',
          id
        );
      }

      const resource = await mcpBridge.readResource(params.uri);

      const result = {
        contents: [resource]
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Failed to read resource',
        error.message,
        id
      );
    }
  }

  /**
   * Handle prompts/list method
   */
  async handlePromptsList(params, id, mcpBridge) {
    try {
      const prompts = await mcpBridge.getAllPrompts();

      const result = {
        prompts
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Failed to list prompts',
        error.message,
        id
      );
    }
  }

  /**
   * Handle prompts/get method
   */
  async handlePromptsGet(params, id, mcpBridge) {
    try {
      if (!params?.name) {
        return this.createErrorResponse(
          this.ERROR_CODES.INVALID_PARAMS,
          'Invalid params',
          'Prompt name is required',
          id
        );
      }

      const prompt = await mcpBridge.getPrompt(params.name, params.arguments);

      const result = {
        description: prompt.description,
        messages: prompt.messages
      };

      return this.createSuccessResponse(result, id);

    } catch (error) {
      return this.createErrorResponse(
        this.ERROR_CODES.MCP_SERVER_ERROR,
        'Failed to get prompt',
        error.message,
        id
      );
    }
  }

  /**
   * Validate request parameters against schema
   */
  validateParams(params, schema) {
    if (!schema) return true;

    // Basic validation - extend with ajv or similar for production
    if (schema.required) {
      for (const field of schema.required) {
        if (!(field in params)) {
          throw new Error(`Missing required parameter: ${field}`);
        }
      }
    }

    return true;
  }
}