#!/usr/bin/env python3
"""
MCP Connection Manager

Handles connections and communication with multiple MCP servers.
Provides connection pooling, error handling, and health monitoring.
"""

import asyncio
import subprocess
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from utils import setup_logger, utc_now

logger = setup_logger("mcp-manager")


class MCPConnection:
    """Individual MCP server connection"""

    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self.process: Optional[subprocess.Popen] = None
        self.connected = False
        self.last_ping: Optional[datetime] = None
        self.error_count = 0

    async def connect(self) -> bool:
        """Connect to MCP server"""
        try:
            logger.info(f"Starting MCP server: {self.name}")

            # Start the MCP server process
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )

            # Wait a moment for server to start
            await asyncio.sleep(1)

            # Check if process is still running
            if self.process.poll() is None:
                self.connected = True
                self.last_ping = utc_now()
                logger.info(f"Connected to {self.name}")
                return True
            else:
                stderr_output = self.process.stderr.read() if self.process.stderr else "No error output"
                logger.error(f"Failed to start {self.name}: {stderr_output}")
                return False

        except Exception as e:
            logger.error(f"Error connecting to {self.name}: {e}")
            return False

    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request to MCP server"""
        if not self.connected or not self.process:
            raise Exception(f"Not connected to {self.name}")

        if params is None:
            params = {}

        request = {
            "jsonrpc": "2.0",
            "id": int(utc_now().timestamp() * 1000000),  # Microsecond timestamp as ID
            "method": method,
            "params": params
        }

        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # Read response (with timeout)
            response_line = await asyncio.wait_for(
                self._read_line_async(),
                timeout=30.0
            )

            if not response_line:
                raise Exception("No response from server")

            response = json.loads(response_line)

            # Update ping time
            self.last_ping = utc_now()

            # Check for errors
            if "error" in response:
                error = response["error"]
                raise Exception(f"MCP Error: {error.get('message', 'Unknown error')}")

            return response.get("result", {})

        except asyncio.TimeoutError:
            self.error_count += 1
            raise Exception(f"Request timeout for {self.name}")
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error sending request to {self.name}: {e}")
            raise

    async def _read_line_async(self) -> str:
        """Read a line from stdout asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process.stdout.readline)

    async def ping(self) -> bool:
        """Ping server to check health"""
        try:
            # Try to call a simple method (this would be server-specific)
            await self.send_request("ping")
            return True
        except:
            return False

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.process:
            logger.info(f"Disconnecting from {self.name}")

            try:
                # Try graceful shutdown first
                self.process.terminate()
                await asyncio.sleep(2)

                # Force kill if still running
                if self.process.poll() is None:
                    self.process.kill()

                self.process.wait()  # Clean up process

            except Exception as e:
                logger.error(f"Error disconnecting from {self.name}: {e}")

            finally:
                self.connected = False
                self.process = None
                logger.info(f"Disconnected from {self.name}")


class MCPServerManager:
    """Manages multiple MCP server connections"""

    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.health_check_interval = 60  # seconds
        self.health_check_task: Optional[asyncio.Task] = None

    def add_server(self, name: str, command: str, args: List[str]):
        """Add MCP server configuration"""
        self.connections[name] = MCPConnection(name, command, args)
        logger.info(f"Added MCP server config: {name}")

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured MCP servers"""
        logger.info("Connecting to all MCP servers...")

        connection_results = {}
        connection_tasks = []

        for name, connection in self.connections.items():
            task = asyncio.create_task(connection.connect())
            connection_tasks.append((name, task))

        # Wait for all connections to complete
        for name, task in connection_tasks:
            try:
                result = await task
                connection_results[name] = result

                if result:
                    logger.info(f"✓ Connected to {name}")
                else:
                    logger.error(f"✗ Failed to connect to {name}")

            except Exception as e:
                logger.error(f"✗ Error connecting to {name}: {e}")
                connection_results[name] = False

        # Start health monitoring
        await self.start_health_monitoring()

        successful_connections = sum(connection_results.values())
        total_connections = len(connection_results)

        logger.info(f"Connection summary: {successful_connections}/{total_connections} successful")

        return connection_results

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_name not in self.connections:
            raise Exception(f"Server {server_name} not configured")

        connection = self.connections[server_name]

        if not connection.connected:
            raise Exception(f"Server {server_name} not connected")

        try:
            # Call the tool
            result = await connection.send_request("tools/call", {
                "name": tool_name,
                "arguments": kwargs
            })

            logger.debug(f"Called {tool_name} on {server_name}")
            return result

        except Exception as e:
            logger.error(f"Error calling {tool_name} on {server_name}: {e}")

            # Try to reconnect if connection seems broken
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                logger.info(f"Attempting to reconnect to {server_name}")
                await connection.disconnect()
                if await connection.connect():
                    logger.info(f"Reconnected to {server_name}")
                    # Retry the call once
                    try:
                        return await connection.send_request("tools/call", {
                            "name": tool_name,
                            "arguments": kwargs
                        })
                    except Exception as retry_error:
                        logger.error(f"Retry failed for {server_name}: {retry_error}")
                        raise retry_error

            raise e

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List available tools on a server"""
        if server_name not in self.connections:
            raise Exception(f"Server {server_name} not configured")

        connection = self.connections[server_name]

        if not connection.connected:
            raise Exception(f"Server {server_name} not connected")

        try:
            result = await connection.send_request("tools/list")
            return result.get("tools", [])

        except Exception as e:
            logger.error(f"Error listing tools for {server_name}: {e}")
            raise

    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all MCP servers"""
        status = {}

        for name, connection in self.connections.items():
            status[name] = {
                "connected": connection.connected,
                "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
                "error_count": connection.error_count,
                "process_running": connection.process is not None and connection.process.poll() is None
            }

        return status

    async def start_health_monitoring(self):
        """Start background health monitoring"""
        if self.health_check_task is None or self.health_check_task.done():
            self.health_check_task = asyncio.create_task(self._health_monitor_loop())
            logger.info("Started MCP server health monitoring")

    async def _health_monitor_loop(self):
        """Background health monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                for name, connection in self.connections.items():
                    if connection.connected:
                        try:
                            # Check if connection is still healthy
                            if connection.last_ping:
                                time_since_ping = utc_now() - connection.last_ping
                                if time_since_ping > timedelta(minutes=5):
                                    logger.warning(f"No recent activity from {name} ({time_since_ping})")

                            # Try to ping the server
                            if not await connection.ping():
                                logger.warning(f"Health check failed for {name}")

                                # Try to reconnect
                                logger.info(f"Attempting to reconnect to {name}")
                                await connection.disconnect()
                                if await connection.connect():
                                    logger.info(f"Successfully reconnected to {name}")
                                else:
                                    logger.error(f"Failed to reconnect to {name}")

                        except Exception as e:
                            logger.error(f"Health check error for {name}: {e}")

            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        logger.info("Disconnecting from all MCP servers...")

        # Stop health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Disconnect all servers
        disconnect_tasks = []
        for connection in self.connections.values():
            if connection.connected:
                disconnect_tasks.append(connection.disconnect())

        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        logger.info("Disconnected from all MCP servers")

    async def restart_server(self, server_name: str) -> bool:
        """Restart a specific MCP server"""
        if server_name not in self.connections:
            raise Exception(f"Server {server_name} not configured")

        connection = self.connections[server_name]

        logger.info(f"Restarting MCP server: {server_name}")

        # Disconnect first
        await connection.disconnect()

        # Wait a moment
        await asyncio.sleep(2)

        # Reconnect
        success = await connection.connect()

        if success:
            logger.info(f"Successfully restarted {server_name}")
        else:
            logger.error(f"Failed to restart {server_name}")

        return success


# Example usage and testing functions
async def test_mcp_manager():
    """Test MCP manager functionality"""
    manager = MCPServerManager()

    # Add test servers (these would be real MCP servers in practice)
    manager.add_server("test1", "python", ["-c", "import time; time.sleep(60)"])
    manager.add_server("test2", "python", ["-c", "import time; time.sleep(60)"])

    # Connect to all servers
    results = await manager.connect_all()
    print("Connection results:", results)

    # Get server status
    status = await manager.get_server_status()
    print("Server status:", status)

    # Wait a bit
    await asyncio.sleep(5)

    # Disconnect
    await manager.disconnect_all()


if __name__ == "__main__":
    # Run test
    asyncio.run(test_mcp_manager())