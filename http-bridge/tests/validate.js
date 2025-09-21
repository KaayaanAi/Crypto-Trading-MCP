#!/usr/bin/env node

/**
 * MCP HTTP Bridge Validation Tests
 *
 * Tests basic functionality, JSON-RPC 2.0 compliance, and n8n integration
 */

import { execSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = join(__dirname, '..');

class ValidationTests {
  constructor() {
    this.passed = 0;
    this.failed = 0;
    this.errors = [];
  }

  log(message, type = 'info') {
    const colors = {
      info: '\x1b[36m',    // cyan
      pass: '\x1b[32m',    // green
      fail: '\x1b[31m',    // red
      warn: '\x1b[33m',    // yellow
      reset: '\x1b[0m'     // reset
    };

    console.log(`${colors[type]}${message}${colors.reset}`);
  }

  test(description, testFn) {
    try {
      testFn();
      this.passed++;
      this.log(`✅ ${description}`, 'pass');
    } catch (error) {
      this.failed++;
      this.errors.push({ description, error: error.message });
      this.log(`❌ ${description}: ${error.message}`, 'fail');
    }
  }

  async validateProject() {
    this.log('🔍 Validating Crypto Trading MCP HTTP Bridge...', 'info');
    this.log('', 'info');

    // Test project structure
    this.test('package.json exists', () => {
      if (!existsSync(join(rootDir, 'package.json'))) {
        throw new Error('package.json not found');
      }
    });

    this.test('server.js exists', () => {
      if (!existsSync(join(rootDir, 'server.js'))) {
        throw new Error('server.js not found');
      }
    });

    this.test('json-rpc-handler.js exists', () => {
      if (!existsSync(join(rootDir, 'json-rpc-handler.js'))) {
        throw new Error('json-rpc-handler.js not found');
      }
    });

    this.test('mcp-bridge.js exists', () => {
      if (!existsSync(join(rootDir, 'mcp-bridge.js'))) {
        throw new Error('mcp-bridge.js not found');
      }
    });

    this.test('config.js exists', () => {
      if (!existsSync(join(rootDir, 'config.js'))) {
        throw new Error('config.js not found');
      }
    });

    this.test('.env.example exists', () => {
      if (!existsSync(join(rootDir, '.env.example'))) {
        throw new Error('.env.example not found');
      }
    });

    // Test package.json content
    this.test('package.json has correct structure', () => {
      const pkg = JSON.parse(readFileSync(join(rootDir, 'package.json'), 'utf8'));

      if (pkg.type !== 'module') {
        throw new Error('package.json must have "type": "module"');
      }

      if (!pkg.engines?.node) {
        throw new Error('package.json must specify Node.js engine requirement');
      }

      const requiredDeps = [
        '@modelcontextprotocol/sdk',
        'express',
        'ws',
        'cors',
        'helmet',
        'dotenv'
      ];

      for (const dep of requiredDeps) {
        if (!pkg.dependencies?.[dep]) {
          throw new Error(`Missing required dependency: ${dep}`);
        }
      }
    });

    // Test Node.js version
    this.test('Node.js version >= 20.0.0', () => {
      const version = process.version;
      const majorVersion = parseInt(version.slice(1).split('.')[0]);

      if (majorVersion < 20) {
        throw new Error(`Node.js ${version} is too old. Requires >= 20.0.0`);
      }
    });

    // Test npm version
    this.test('npm version >= 10.0.0', () => {
      try {
        const npmVersion = execSync('npm --version', { encoding: 'utf8' }).trim();
        const majorVersion = parseInt(npmVersion.split('.')[0]);

        if (majorVersion < 10) {
          throw new Error(`npm ${npmVersion} is too old. Requires >= 10.0.0`);
        }
      } catch (error) {
        throw new Error('npm not found or not accessible');
      }
    });

    // Test Python availability
    this.test('Python 3 available', () => {
      try {
        const pythonVersion = execSync('python3 --version', { encoding: 'utf8' }).trim();
        if (!pythonVersion.includes('Python 3.')) {
          throw new Error('Python 3 not found');
        }
      } catch (error) {
        throw new Error('python3 command not found');
      }
    });

    // Test MCP server files exist
    const servers = ['binance-mcp', 'crypto-technical-mcp', 'crypto-news-mcp',
                    'crypto-social-mcp', 'crypto-risk-mcp', 'crypto-ai-mcp'];

    for (const server of servers) {
      this.test(`${server} main.py exists`, () => {
        const serverPath = join(rootDir, '..', 'servers', server, 'main.py');
        if (!existsSync(serverPath)) {
          throw new Error(`${server}/main.py not found at ${serverPath}`);
        }
      });
    }

    // Test requirements.txt
    this.test('Python requirements.txt exists', () => {
      const reqPath = join(rootDir, '..', 'requirements.txt');
      if (!existsSync(reqPath)) {
        throw new Error('requirements.txt not found');
      }
    });

    // Syntax validation
    this.test('JavaScript syntax validation', () => {
      const files = ['server.js', 'json-rpc-handler.js', 'mcp-bridge.js', 'config.js'];

      for (const file of files) {
        try {
          const filePath = join(rootDir, file);
          // Properly quote file paths to handle spaces in directory names
          execSync(`node --check "${filePath}"`, { stdio: 'pipe' });
        } catch (error) {
          throw new Error(`Syntax error in ${file}: ${error.message}`);
        }
      }
    });

    // JSON-RPC 2.0 compliance test
    this.test('JSON-RPC 2.0 request validation', async () => {
      // Import and test the JSON-RPC handler
      const { JsonRpcHandler } = await import('../json-rpc-handler.js');
      const handler = new JsonRpcHandler({ info: () => {}, error: () => {}, debug: () => {} });

      // Valid request
      const validRequest = {
        jsonrpc: '2.0',
        method: 'tools/list',
        id: 1
      };

      if (!handler.isValidRequest(validRequest)) {
        throw new Error('Valid JSON-RPC 2.0 request rejected');
      }

      // Invalid requests
      const invalidRequests = [
        { method: 'test' }, // missing jsonrpc
        { jsonrpc: '1.0', method: 'test', id: 1 }, // wrong version
        { jsonrpc: '2.0', id: 1 }, // missing method
        { jsonrpc: '2.0', method: 'test' } // missing id
      ];

      for (const invalid of invalidRequests) {
        if (handler.isValidRequest(invalid)) {
          throw new Error(`Invalid request accepted: ${JSON.stringify(invalid)}`);
        }
      }
    });

    // Environment validation
    this.test('Environment file template validation', () => {
      const envExample = readFileSync(join(rootDir, '.env.example'), 'utf8');

      const requiredVars = [
        'MCP_HOST',
        'MCP_PORT',
        'BINANCE_API_KEY',
        'BINANCE_SECRET_KEY',
        'PYTHON_PATH'
      ];

      for (const varName of requiredVars) {
        if (!envExample.includes(varName)) {
          throw new Error(`Missing environment variable in .env.example: ${varName}`);
        }
      }
    });

    this.printResults();
  }

  printResults() {
    this.log('', 'info');
    this.log('📊 Validation Results:', 'info');
    this.log(`✅ Passed: ${this.passed}`, 'pass');
    this.log(`❌ Failed: ${this.failed}`, this.failed > 0 ? 'fail' : 'info');

    if (this.errors.length > 0) {
      this.log('', 'info');
      this.log('🔍 Error Details:', 'warn');
      for (const error of this.errors) {
        this.log(`  • ${error.description}: ${error.error}`, 'fail');
      }
    }

    if (this.failed === 0) {
      this.log('', 'info');
      this.log('🎉 All validations passed! Ready for n8n integration.', 'pass');
      this.log('', 'info');
      this.log('Next steps:', 'info');
      this.log('1. Copy .env.example to .env and configure your API keys', 'info');
      this.log('2. Run: npm install', 'info');
      this.log('3. Run: npm start', 'info');
      this.log('4. Test with: curl -X POST http://localhost:8080/health', 'info');
      process.exit(0);
    } else {
      this.log('', 'info');
      this.log('❌ Some validations failed. Please fix the issues above.', 'fail');
      process.exit(1);
    }
  }
}

// Run validation
const validator = new ValidationTests();
validator.validateProject().catch(error => {
  console.error('Validation error:', error);
  process.exit(1);
});