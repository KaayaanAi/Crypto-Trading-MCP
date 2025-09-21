# Changelog

All notable changes to the Crypto Trading MCP System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-09-21

### Added
- **HTTP Bridge for n8n Integration**: Complete HTTP-to-MCP bridge allowing integration with n8n workflows
  - Express.js server with WebSocket support
  - RESTful API endpoints for all MCP servers
  - Rate limiting and security middleware
  - Health check endpoints
  - Docker deployment configuration
- **Quality Assurance Tools**: Integrated Qlty code quality monitoring
- **Comprehensive Error Handling**: Standardized error handling across all components
  - Custom exception hierarchy with proper error codes
  - Centralized error response formatting
  - Graceful degradation mechanisms
- **Test Suite Enhancement**: Added comprehensive error handling validation tests
- **Docker HTTP Deployment**: New Dockerfile.http and docker-compose.http.yml for HTTP bridge

### Fixed
- **Critical SSL Security Vulnerability**: Completely resolved SSL certificate bypass issues
  - Removed `ssl.CERT_NONE` and `check_hostname = False` from all files
  - Implemented secure SSL context creation with proper validation
  - Added environment-based SSL control for development flexibility
  - Applied fixes to Binance MCP server, crypto trader client, and test scripts
- **Runtime Error Protection**: Fixed 6 critical runtime errors
  - Division by zero protection in Kelly fraction calculations
  - Array bounds checking in RSS feed parsing
  - Error severity enum case matching
  - Exception constructor conflicts in RiskLimitExceededError
  - Stack overflow prevention in rate limiter recursion
  - Shell script compatibility for cross-platform testing
- **Code Quality Issues**: Resolved 38+ formatting and style violations
  - Import order standardization across all Python modules
  - Unused import cleanup in servers and shared modules
  - Type annotation improvements in utility functions
  - PEP 8 compliance with Black formatting
- **Configuration Vulnerabilities**:
  - Docker package version pinning for security (Alpine packages)
  - Node.js dependency management (removed "latest" versions)
  - Missing Docker mount directories created

### Changed
- **Dependency Management**: Updated all Python and Node.js dependencies to latest stable versions
  - Python: aiohttp, pydantic, structlog, backoff, tenacity updated
  - Node.js: Express 4.19.2, Axios 1.7.7, other dependencies pinned to semantic versions
- **Constants Migration**: Moved hardcoded values to centralized constants.py
  - Trading parameters centralized
  - API endpoints and timeouts standardized
  - Error codes and messages unified
- **Project Structure**: Reorganized files for better maintainability
  - Moved test files to tests/ directory
  - Centralized shared utilities and types
  - Improved module organization and imports

### Security
- **SSL/TLS Security**: Complete SSL security implementation
  - TLS 1.2+ minimum version enforcement
  - Proper certificate validation in all HTTP/WebSocket connections
  - Environment-controlled SSL verification for development
  - No hardcoded certificate bypasses
- **Container Security**: Enhanced Docker security
  - Non-root user execution in containers
  - Package version pinning to prevent supply chain attacks
  - Secure network isolation between services
- **Secret Management**: Improved credential handling
  - No hardcoded secrets in codebase
  - Comprehensive .env.example templates
  - Proper environment variable validation

### Performance
- **Resource Management**: Optimized system resource usage
  - Connection pooling for HTTP requests
  - Memory leak prevention in async operations
  - Efficient rate limiting algorithms
  - Bounded queues and connection limits
- **Cache Management**: Implemented intelligent caching
  - TTL-based cache with size limits
  - Automatic cleanup of stale entries
  - Resource-aware garbage collection

### Technical Debt
- **Code Standardization**: Achieved consistent code style across all modules
  - Centralized exception handling patterns
  - Unified logging configuration
  - Standardized async/await patterns
- **Test Coverage**: Expanded test coverage to include edge cases
  - Error boundary testing
  - Network failure simulation
  - Resource exhaustion scenarios

## [1.0.0] - 2025-09-13

### Added
- Initial release of Crypto Trading MCP System
- 6 specialized MCP servers:
  - crypto-news-mcp: RSS feeds and news sentiment analysis
  - crypto-technical-mcp: Technical indicators and chart patterns
  - crypto-social-mcp: Social sentiment analysis
  - binance-mcp: Exchange integration and order execution
  - crypto-risk-mcp: Risk management and position sizing
  - crypto-ai-mcp: AI-powered market analysis with Ollama
- Main trading client with orchestration capabilities
- Docker deployment configuration
- Basic documentation and setup instructions

### Security
- Basic API key management
- Environment variable configuration
- Initial SSL/TLS setup (later fixed in v1.1.0)

---

## Migration Guide

### From v1.0.0 to v1.1.0

1. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd http-bridge && npm install
   ```

2. **Environment Variables**: No new required variables, but recommended:
   ```bash
   # Optional: Control SSL verification for development
   DISABLE_SSL_VERIFICATION=false  # Default: secure
   ```

3. **Docker Deployment**: New HTTP bridge option available:
   ```bash
   # Traditional MCP deployment
   docker-compose up -d

   # New HTTP bridge deployment (for n8n integration)
   docker-compose -f docker-compose.http.yml up -d
   ```

4. **Breaking Changes**: None - fully backward compatible

5. **New Features**: HTTP bridge available at `http://localhost:8080` when using HTTP deployment

---

## Support

- **Issues**: Report bugs via GitHub Issues
- **Documentation**: See [docs/](./docs/) directory
- **API Reference**: See [docs/API_REFERENCE.md](./docs/API_REFERENCE.md)
- **Quick Start**: See [docs/QUICK_START.md](./docs/QUICK_START.md)