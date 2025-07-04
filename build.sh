#!/bin/bash

# Build script for Distributed Edge AI Network
# Supports Python, JavaScript, and C++ components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_ROOT=$(pwd)
BUILD_DIR="${PROJECT_ROOT}/build"
PYTHON_ENV="${PROJECT_ROOT}/venv"
NODE_MODULES="${PROJECT_ROOT}/web/dashboard/node_modules"
CPP_BUILD_DIR="${PROJECT_ROOT}/cpp/build"

# Parse command line arguments
BUILD_PYTHON=true
BUILD_JAVASCRIPT=true
BUILD_CPP=true
INSTALL_DEPS=true
RUN_TESTS=false
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --python-only)
            BUILD_PYTHON=true
            BUILD_JAVASCRIPT=false
            BUILD_CPP=false
            shift
            ;;
        --javascript-only)
            BUILD_PYTHON=false
            BUILD_JAVASCRIPT=true
            BUILD_CPP=false
            shift
            ;;
        --cpp-only)
            BUILD_PYTHON=false
            BUILD_JAVASCRIPT=false
            BUILD_CPP=true
            shift
            ;;
        --no-deps)
            INSTALL_DEPS=false
            shift
            ;;
        --with-tests)
            RUN_TESTS=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --python-only     Build only Python components"
            echo "  --javascript-only Build only JavaScript components"
            echo "  --cpp-only        Build only C++ components"
            echo "  --no-deps         Skip dependency installation"
            echo "  --with-tests      Run tests after building"
            echo "  --clean           Clean build directories first"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Clean build directories if requested
if [ "$CLEAN_BUILD" = true ]; then
    log_info "Cleaning build directories..."
    rm -rf "$BUILD_DIR"
    rm -rf "$CPP_BUILD_DIR"
    rm -rf "$NODE_MODULES"
    if [ -d "$PYTHON_ENV" ]; then
        rm -rf "$PYTHON_ENV"
    fi
    log_success "Build directories cleaned"
fi

# Create build directory
mkdir -p "$BUILD_DIR"

# Check system requirements
log_info "Checking system requirements..."

# Check Python
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: $PYTHON_VERSION"
else
    log_error "Python 3 is required but not installed"
    exit 1
fi

# Check Node.js (if building JavaScript)
if [ "$BUILD_JAVASCRIPT" = true ]; then
    if command -v node >/dev/null 2>&1; then
        NODE_VERSION=$(node --version)
        log_info "Node.js version: $NODE_VERSION"
    else
        log_error "Node.js is required but not installed"
        exit 1
    fi
fi

# Check C++ compiler (if building C++)
if [ "$BUILD_CPP" = true ]; then
    if command -v g++ >/dev/null 2>&1; then
        GCC_VERSION=$(g++ --version | head -n1)
        log_info "GCC version: $GCC_VERSION"
    else
        log_error "g++ is required but not installed"
        exit 1
    fi
    
    # Check CMake
    if command -v cmake >/dev/null 2>&1; then
        CMAKE_VERSION=$(cmake --version | head -n1)
        log_info "CMake version: $CMAKE_VERSION"
    else
        log_error "CMake is required but not installed"
        exit 1
    fi
fi

# Build Python components
if [ "$BUILD_PYTHON" = true ]; then
    log_info "Building Python components..."
    
    # Create virtual environment
    if [ ! -d "$PYTHON_ENV" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv "$PYTHON_ENV"
        log_success "Python virtual environment created"
    fi
    
    # Activate virtual environment
    source "$PYTHON_ENV/bin/activate"
    
    # Install dependencies
    if [ "$INSTALL_DEPS" = true ]; then
        log_info "Installing Python dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    fi
    
    # Install package in development mode
    log_info "Installing package in development mode..."
    pip install -e .
    log_success "Python package installed"
    
    # Run Python tests
    if [ "$RUN_TESTS" = true ]; then
        log_info "Running Python tests..."
        if [ -d "tests" ]; then
            python -m pytest tests/ -v
            log_success "Python tests completed"
        else
            log_warning "No Python tests found"
        fi
    fi
    
    log_success "Python components built successfully"
fi

# Build JavaScript components
if [ "$BUILD_JAVASCRIPT" = true ]; then
    log_info "Building JavaScript components..."
    
    cd "${PROJECT_ROOT}/web/dashboard"
    
    # Install dependencies
    if [ "$INSTALL_DEPS" = true ]; then
        log_info "Installing JavaScript dependencies..."
        npm install
        log_success "JavaScript dependencies installed"
    fi
    
    # Build production bundle (if build script exists)
    if grep -q "build" package.json; then
        log_info "Building production bundle..."
        npm run build
        log_success "JavaScript bundle built"
    fi
    
    # Run JavaScript tests
    if [ "$RUN_TESTS" = true ]; then
        log_info "Running JavaScript tests..."
        if grep -q "test" package.json; then
            npm test
            log_success "JavaScript tests completed"
        else
            log_warning "No JavaScript tests found"
        fi
    fi
    
    cd "$PROJECT_ROOT"
    log_success "JavaScript components built successfully"
fi

# Build C++ components
if [ "$BUILD_CPP" = true ]; then
    log_info "Building C++ components..."
    
    # Create C++ build directory
    mkdir -p "$CPP_BUILD_DIR"
    cd "$CPP_BUILD_DIR"
    
    # Configure with CMake
    log_info "Configuring C++ build with CMake..."
    cmake ../
    
    # Build
    log_info "Compiling C++ components..."
    make -j$(nproc)
    
    # Install
    log_info "Installing C++ components..."
    make install
    
    # Copy library to Python directory for integration
    if [ -f "edge_processor_lib.so" ]; then
        cp edge_processor_lib.so "${PROJECT_ROOT}/src/common/"
        log_success "C++ library copied to Python directory"
    fi
    
    cd "$PROJECT_ROOT"
    log_success "C++ components built successfully"
fi

# Create deployment package
log_info "Creating deployment package..."
cd "$BUILD_DIR"

# Copy Python source
if [ "$BUILD_PYTHON" = true ]; then
    cp -r "${PROJECT_ROOT}/src" .
    cp -r "${PROJECT_ROOT}/config" .
    cp "${PROJECT_ROOT}/requirements.txt" .
fi

# Copy JavaScript dashboard
if [ "$BUILD_JAVASCRIPT" = true ]; then
    cp -r "${PROJECT_ROOT}/web" .
fi

# Copy C++ binaries
if [ "$BUILD_CPP" = true ]; then
    mkdir -p cpp
    if [ -f "${CPP_BUILD_DIR}/edge_processor" ]; then
        cp "${CPP_BUILD_DIR}/edge_processor" cpp/
    fi
    if [ -f "${CPP_BUILD_DIR}/edge_processor_lib.so" ]; then
        cp "${CPP_BUILD_DIR}/edge_processor_lib.so" cpp/
    fi
fi

# Copy documentation
cp "${PROJECT_ROOT}/README.md" .
cp "${PROJECT_ROOT}/MULTI_LANGUAGE.md" .

# Create startup scripts
log_info "Creating startup scripts..."

# Python startup script
cat > start_coordinator.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source ../venv/bin/activate
python -m src.coordinator.main
EOF

cat > start_edge_node.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source ../venv/bin/activate
python -m src.edge_node.main
EOF

# JavaScript startup script
cat > start_dashboard.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/web/dashboard"
node server.js
EOF

# Make scripts executable
chmod +x start_coordinator.sh start_edge_node.sh start_dashboard.sh

# Create Docker support files
log_info "Creating Docker support files..."

# Dockerfile
cat > Dockerfile << 'EOF'
FROM ubuntu:20.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nodejs \
    npm \
    g++ \
    cmake \
    libopencv-dev \
    libasound2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install Python dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Install JavaScript dependencies
RUN cd web/dashboard && npm install

# Build C++ components
RUN mkdir -p cpp/build && \
    cd cpp/build && \
    cmake ../ && \
    make -j$(nproc)

# Expose ports
EXPOSE 5000 3000 8080

# Default command
CMD ["bash"]
EOF

# Docker Compose
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  coordinator:
    build: .
    ports:
      - "5000:5000"
    command: bash start_coordinator.sh
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
  
  dashboard:
    build: .
    ports:
      - "3000:3000"
    command: bash start_dashboard.sh
    depends_on:
      - coordinator
  
  edge_node:
    build: .
    command: bash start_edge_node.sh
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - coordinator
EOF

cd "$PROJECT_ROOT"
log_success "Deployment package created in $BUILD_DIR"

# Generate build report
log_info "Generating build report..."
cat > "${BUILD_DIR}/build_report.txt" << EOF
Distributed Edge AI Network - Build Report
==========================================

Build Date: $(date)
Project Root: $PROJECT_ROOT
Build Directory: $BUILD_DIR

Components Built:
- Python: $BUILD_PYTHON
- JavaScript: $BUILD_JAVASCRIPT
- C++: $BUILD_CPP

Dependencies Installed: $INSTALL_DEPS
Tests Run: $RUN_TESTS
Clean Build: $CLEAN_BUILD

System Information:
- OS: $(uname -s)
- Architecture: $(uname -m)
- Python Version: $PYTHON_VERSION
EOF

if [ "$BUILD_JAVASCRIPT" = true ]; then
    echo "- Node.js Version: $NODE_VERSION" >> "${BUILD_DIR}/build_report.txt"
fi

if [ "$BUILD_CPP" = true ]; then
    echo "- GCC Version: $GCC_VERSION" >> "${BUILD_DIR}/build_report.txt"
    echo "- CMake Version: $CMAKE_VERSION" >> "${BUILD_DIR}/build_report.txt"
fi

log_success "Build completed successfully!"
log_info "Build report saved to: ${BUILD_DIR}/build_report.txt"
log_info "To run the system:"
log_info "  Coordinator: cd build && ./start_coordinator.sh"
log_info "  Dashboard: cd build && ./start_dashboard.sh"
log_info "  Edge Node: cd build && ./start_edge_node.sh"
log_info "  Docker: cd build && docker-compose up"
