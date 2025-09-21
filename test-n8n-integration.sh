#!/bin/bash

# Test n8n MCP Integration Script
# Tests the HTTP bridge endpoints for n8n compatibility

set -e

echo "🧪 Testing Crypto Trading MCP HTTP Bridge for n8n Integration"
echo "=============================================================="

# Configuration
MCP_URL="${MCP_URL:-http://localhost:8080}"
TEST_TIMEOUT=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Test function
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"

    log_info "Testing: $test_name"

    if [ -z "$data" ]; then
        # GET request
        response=$(curl -s -w "\n%{http_code}" -m $TEST_TIMEOUT "$url" 2>/dev/null || echo -e "\n000")
    else
        # POST request
        response=$(curl -s -w "\n%{http_code}" -m $TEST_TIMEOUT -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$url" 2>/dev/null || echo -e "\n000")
    fi

    # Extract response body and status code
    status_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)

    if [ "$status_code" = "$expected_status" ]; then
        log_success "$test_name - Status: $status_code"
        return 0
    else
        log_error "$test_name - Expected: $expected_status, Got: $status_code"
        if [ "$status_code" = "000" ]; then
            log_error "  Connection failed or timeout"
        elif [ -n "$response_body" ]; then
            echo "  Response: $(echo "$response_body" | head -c 200)"
        fi
        return 1
    fi
}

# Test JSON-RPC 2.0 request
test_jsonrpc() {
    local test_name="$1"
    local method="$2"
    local params="$3"
    local expected_field="$4"

    log_info "Testing JSON-RPC: $test_name"

    local json_data="{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"id\":1"
    if [ -n "$params" ]; then
        json_data="$json_data,\"params\":$params"
    fi
    json_data="$json_data}"

    response=$(curl -s -m $TEST_TIMEOUT -X POST \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        "$MCP_URL/mcp" 2>/dev/null || echo "{\"error\":\"connection_failed\"}")

    # Check if response contains expected field
    if echo "$response" | grep -q "\"$expected_field\""; then
        log_success "$test_name - Found: $expected_field"
        return 0
    else
        log_error "$test_name - Missing: $expected_field"
        echo "  Response: $(echo "$response" | head -c 200)"
        return 1
    fi
}

echo ""
log_info "Step 1: Basic HTTP Endpoint Tests"
echo "-----------------------------------"

# Test health endpoint
test_endpoint "Health Check" "GET" "$MCP_URL/health" "" "200"

# Test metrics endpoint
test_endpoint "Metrics Endpoint" "GET" "$MCP_URL/metrics" "" "200"

# Test CORS preflight
test_endpoint "CORS Preflight" "OPTIONS" "$MCP_URL/mcp" "" "204"

# Test invalid endpoint
test_endpoint "404 Handling" "GET" "$MCP_URL/invalid" "" "404"

echo ""
log_info "Step 2: JSON-RPC 2.0 Protocol Tests"
echo "------------------------------------"

# Test invalid JSON-RPC requests
test_endpoint "Invalid JSON-RPC (missing jsonrpc)" "POST" "$MCP_URL/mcp" \
    '{"method":"test","id":1}' "400"

test_endpoint "Invalid JSON-RPC (wrong version)" "POST" "$MCP_URL/mcp" \
    '{"jsonrpc":"1.0","method":"test","id":1}' "400"

test_endpoint "Invalid JSON-RPC (missing method)" "POST" "$MCP_URL/mcp" \
    '{"jsonrpc":"2.0","id":1}' "400"

test_endpoint "Invalid JSON-RPC (missing id)" "POST" "$MCP_URL/mcp" \
    '{"jsonrpc":"2.0","method":"test"}' "400"

echo ""
log_info "Step 3: MCP Protocol Method Tests"
echo "----------------------------------"

# Test MCP methods
test_jsonrpc "Initialize Method" "initialize" '{}' "protocolVersion"

test_jsonrpc "Tools List Method" "tools/list" '' "tools"

test_jsonrpc "Invalid Method" "invalid/method" '' "error"

# Test tools/call with invalid tool
test_jsonrpc "Tools Call - Invalid Tool" "tools/call" \
    '{"name":"invalid_tool","arguments":{}}' "error"

echo ""
log_info "Step 4: n8n Compatibility Tests"
echo "--------------------------------"

# Test content-type handling
log_info "Testing Content-Type handling"
response=$(curl -s -w "\n%{http_code}" -m $TEST_TIMEOUT -X POST \
    -H "Content-Type: application/json; charset=utf-8" \
    -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    "$MCP_URL/mcp" 2>/dev/null || echo -e "\n000")

status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "200" ]; then
    log_success "Content-Type with charset - Status: 200"
else
    log_error "Content-Type with charset - Status: $status_code"
fi

# Test CORS headers
log_info "Testing CORS headers"
headers=$(curl -s -I -m $TEST_TIMEOUT -X POST \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:5678" \
    "$MCP_URL/mcp" 2>/dev/null || echo "")

if echo "$headers" | grep -qi "access-control-allow-origin"; then
    log_success "CORS headers present"
else
    log_error "CORS headers missing"
fi

# Test large request handling
log_info "Testing large request handling"
large_data='{"jsonrpc":"2.0","method":"tools/list","id":1,"params":{"large_field":"'
for i in {1..100}; do
    large_data="${large_data}large_data_"
done
large_data="${large_data}\"}}"

response=$(curl -s -w "\n%{http_code}" -m $TEST_TIMEOUT -X POST \
    -H "Content-Type: application/json" \
    -d "$large_data" \
    "$MCP_URL/mcp" 2>/dev/null || echo -e "\n000")

status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "200" ]; then
    log_success "Large request handling - Status: 200"
else
    log_error "Large request handling - Status: $status_code"
fi

echo ""
log_info "Step 5: Error Handling Tests"
echo "-----------------------------"

# Test malformed JSON
test_endpoint "Malformed JSON" "POST" "$MCP_URL/mcp" \
    '{"jsonrpc":"2.0","method":}' "400"

# Test empty request
test_endpoint "Empty Request" "POST" "$MCP_URL/mcp" \
    '' "400"

# Test invalid content type
response=$(curl -s -w "\n%{http_code}" -m $TEST_TIMEOUT -X POST \
    -H "Content-Type: text/plain" \
    -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
    "$MCP_URL/mcp" 2>/dev/null || echo -e "\n000")

status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "200" ] || [ "$status_code" = "400" ]; then
    log_success "Invalid Content-Type handling - Status: $status_code"
else
    log_error "Invalid Content-Type handling - Status: $status_code"
fi

echo ""
log_info "Step 6: Performance Tests"
echo "--------------------------"

# Test response time
log_info "Testing response time"
start_time=$(date +%s%N)
curl -s -m $TEST_TIMEOUT "$MCP_URL/health" >/dev/null 2>&1
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds

if [ $response_time -lt 1000 ]; then
    log_success "Response time: ${response_time}ms (< 1000ms)"
else
    log_warning "Response time: ${response_time}ms (> 1000ms)"
fi

# Test concurrent requests
log_info "Testing concurrent requests"
for i in {1..5}; do
    curl -s -m $TEST_TIMEOUT "$MCP_URL/health" >/dev/null 2>&1 &
done
wait

if [ $? -eq 0 ]; then
    log_success "Concurrent requests handled"
else
    log_error "Concurrent requests failed"
fi

echo ""
echo "=============================================================="
log_info "Test Results Summary"
echo "=============================================================="

echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed! The HTTP bridge is ready for n8n integration.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure your .env file with API keys"
    echo "2. Start the services: docker-compose -f docker-compose.http.yml up -d"
    echo "3. In n8n, add MCP Client node with URL: $MCP_URL/mcp"
    echo "4. Test with tools/list method to see available tools"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Please check the HTTP bridge configuration.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if the service is running: curl $MCP_URL/health"
    echo "2. Check logs: docker-compose -f docker-compose.http.yml logs crypto-mcp-bridge"
    echo "3. Verify environment configuration"
    echo ""
    exit 1
fi