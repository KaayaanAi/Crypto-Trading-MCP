#!/bin/bash
"""
Crypto Trading MCP System Startup Script

Starts the complete crypto trading system with all MCP servers.
Supports different deployment modes and environment configurations.
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_CMD="${PYTHON_CMD:-python3}"

# Default configuration
MODE="${1:-development}"
COMPOSE_PROFILES="${COMPOSE_PROFILES:-}"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check Python
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.9" | bc -l) -eq 1 ]]; then
        print_error "Python 3.9+ is required (found $python_version)"
        exit 1
    fi

    print_success "Python $python_version found"

    # Check Docker if using Docker mode
    if [[ "$MODE" == "docker" ]]; then
        if ! command_exists docker; then
            print_error "Docker is required for Docker mode"
            exit 1
        fi

        if ! command_exists docker-compose; then
            print_error "Docker Compose is required for Docker mode"
            exit 1
        fi

        print_success "Docker and Docker Compose found"
    fi

    # Check Ollama for AI features
    if command_exists ollama; then
        print_success "Ollama found for AI analysis"
    else
        print_warning "Ollama not found - AI analysis will be limited"
    fi
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."

    cd "$PROJECT_ROOT"

    # Create .env file if it doesn't exist
    if [[ ! -f .env ]]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your API keys and configuration"
    fi

    # Create necessary directories
    mkdir -p logs
    mkdir -p data
    mkdir -p backups

    print_success "Environment setup complete"
}

# Function to install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."

    cd "$PROJECT_ROOT"

    # Check if virtual environment exists
    if [[ ! -d "venv" ]]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt

    print_success "Dependencies installed"
}

# Function to start native Python mode
start_native() {
    print_status "Starting Crypto Trading MCP System (Native Mode)..."

    cd "$PROJECT_ROOT"

    # Activate virtual environment
    source venv/bin/activate

    # Set environment variables
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # Start Ollama if available and not running
    if command_exists ollama; then
        if ! pgrep -f "ollama serve" > /dev/null; then
            print_status "Starting Ollama server..."
            ollama serve &
            sleep 5
        fi

        # Pull default model if not available
        if ! ollama list | grep -q "llama2"; then
            print_status "Pulling Llama2 model for AI analysis..."
            ollama pull llama2
        fi
    fi

    # Start the main trading client
    print_status "Starting main trading client..."
    python client/crypto_trader.py
}

# Function to start Docker mode
start_docker() {
    print_status "Starting Crypto Trading MCP System (Docker Mode)..."

    cd "$PROJECT_ROOT"

    # Determine Docker Compose profiles
    local profiles=""

    case "$MODE" in
        "docker-full")
            profiles="--profile monitoring --profile with-database"
            ;;
        "docker-monitoring")
            profiles="--profile monitoring"
            ;;
        "docker-database")
            profiles="--profile with-database"
            ;;
    esac

    # Build and start services
    print_status "Building Docker images..."
    docker-compose build

    print_status "Starting services with profiles: $profiles"
    docker-compose up -d $profiles

    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 10

    # Pull Ollama model
    print_status "Setting up Ollama model..."
    docker-compose exec ollama ollama pull llama2

    # Show running services
    print_status "Running services:"
    docker-compose ps

    print_success "Docker deployment started successfully"

    # Show access URLs
    echo ""
    print_status "Service URLs:"
    echo "  - Main System Logs: docker-compose logs -f crypto-trader"
    echo "  - Ollama API: http://localhost:11434"
    echo "  - Redis: localhost:6379"

    if [[ "$profiles" == *"monitoring"* ]]; then
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000 (admin/admin)"
    fi

    if [[ "$profiles" == *"with-database"* ]]; then
        echo "  - MongoDB: localhost:27017"
    fi
}

# Function to stop the system
stop_system() {
    print_status "Stopping Crypto Trading MCP System..."

    cd "$PROJECT_ROOT"

    if [[ -f docker-compose.yml ]] && docker-compose ps | grep -q "Up"; then
        print_status "Stopping Docker services..."
        docker-compose down
        print_success "Docker services stopped"
    fi

    # Kill any remaining Python processes
    pkill -f "crypto_trader.py" || true
    pkill -f "main.py" || true

    print_success "System stopped"
}

# Function to show system status
show_status() {
    print_status "Crypto Trading MCP System Status"
    echo ""

    cd "$PROJECT_ROOT"

    # Check Docker services if Docker Compose exists
    if [[ -f docker-compose.yml ]]; then
        print_status "Docker Services:"
        if docker-compose ps | grep -q "Up"; then
            docker-compose ps
        else
            echo "  No Docker services running"
        fi
        echo ""
    fi

    # Check native processes
    print_status "Native Processes:"
    if pgrep -f "crypto_trader.py" > /dev/null; then
        echo "  ✓ Main trading client is running"
    else
        echo "  ✗ Main trading client is not running"
    fi

    if pgrep -f "ollama serve" > /dev/null; then
        echo "  ✓ Ollama server is running"
    else
        echo "  ✗ Ollama server is not running"
    fi

    echo ""

    # Check log files
    print_status "Recent Logs:"
    if [[ -f logs/crypto_trader.log ]]; then
        echo "  Last 3 lines from main log:"
        tail -3 logs/crypto_trader.log | sed 's/^/    /'
    else
        echo "  No main log file found"
    fi
}

# Function to run tests
run_tests() {
    print_status "Running system tests..."

    cd "$PROJECT_ROOT"

    # Activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi

    # Run Python tests
    if [[ -d "tests" ]]; then
        python -m pytest tests/ -v
    else
        print_warning "No tests directory found"
    fi

    # Test MCP server connections (mock test)
    print_status "Testing MCP server configurations..."
    python -c "
import yaml
import sys
import os

try:
    with open('client/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    mcp_servers = config.get('mcp_servers', {})
    print(f'Found {len(mcp_servers)} MCP server configurations')

    for name, settings in mcp_servers.items():
        enabled = settings.get('enabled', True)
        status = '✓ enabled' if enabled else '✗ disabled'
        print(f'  {name}: {status}')

    print('Configuration test passed')
except Exception as e:
    print(f'Configuration test failed: {e}')
    sys.exit(1)
"

    print_success "Tests completed"
}

# Function to show help
show_help() {
    echo "Crypto Trading MCP System Control Script"
    echo ""
    echo "Usage: $0 [MODE] [COMMAND]"
    echo ""
    echo "Modes:"
    echo "  development    - Native Python development mode (default)"
    echo "  docker         - Basic Docker deployment"
    echo "  docker-full    - Full Docker deployment with monitoring and database"
    echo "  docker-monitoring - Docker with monitoring stack"
    echo "  docker-database   - Docker with database"
    echo ""
    echo "Commands:"
    echo "  start          - Start the system (default)"
    echo "  stop           - Stop the system"
    echo "  restart        - Restart the system"
    echo "  status         - Show system status"
    echo "  test           - Run system tests"
    echo "  logs           - Show recent logs"
    echo "  help           - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Start in development mode"
    echo "  $0 docker start             # Start with Docker"
    echo "  $0 docker-full start        # Start full Docker stack"
    echo "  $0 development stop         # Stop development mode"
    echo "  $0 docker status            # Show Docker status"
}

# Main execution
main() {
    local command="${2:-start}"

    case "$command" in
        "start")
            check_requirements
            setup_environment

            if [[ "$MODE" == "development" ]]; then
                install_dependencies
                start_native
            elif [[ "$MODE" == docker* ]]; then
                start_docker
            else
                print_error "Unknown mode: $MODE"
                show_help
                exit 1
            fi
            ;;
        "stop")
            stop_system
            ;;
        "restart")
            stop_system
            sleep 2
            $0 "$MODE" start
            ;;
        "status")
            show_status
            ;;
        "test")
            check_requirements
            setup_environment
            install_dependencies
            run_tests
            ;;
        "logs")
            if [[ -f docker-compose.yml ]] && docker-compose ps | grep -q "Up"; then
                docker-compose logs -f --tail=100
            elif [[ -f logs/crypto_trader.log ]]; then
                tail -f logs/crypto_trader.log
            else
                print_error "No logs available"
            fi
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"