#!/bin/bash

# Configuration variables
mt5file='/config/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe'
WINEPREFIX='/config/.wine'
WINEDEBUG='-all'
wine_executable="wine"
metatrader_version="5.0.36"
mt5server_port="${MT5_SERVER_PORT:-8001}"
mono_url="https://dl.winehq.org/wine/wine-mono/10.3.0/wine-mono-10.3.0-x86.msi"
python_url="https://www.python.org/ftp/python/3.9.13/python-3.9.13.exe"
mt5setup_url="${MT5_SETUP_URL:-https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe}"

# Build MT5 command line options
# Support both MT5_CMD_OPTIONS and individual MT5_LOGIN, MT5_PASSWORD, MT5_SERVER variables
build_mt5_options() {
    local opts=""

    # Check for individual environment variables first
    if [ -n "${MT5_LOGIN:-}" ]; then
        opts="/login:${MT5_LOGIN}"

        if [ -n "${MT5_PASSWORD:-}" ]; then
            opts="$opts /password:${MT5_PASSWORD}"
        fi

        if [ -n "${MT5_SERVER:-}" ]; then
            opts="$opts /server:${MT5_SERVER}"
        fi

        if [ "${MT5_PORTABLE:-}" = "true" ]; then
            opts="/portable $opts"
        fi

        echo "$opts"
        return
    fi

    # Fall back to MT5_CMD_OPTIONS if individual vars not set
    echo "${MT5_CMD_OPTIONS:-}"
}

# Function to display a graphical message
show_message() {
    echo $1
}

# Function to check if a dependency is installed
check_dependency() {
    if ! command -v $1 &> /dev/null; then
        echo "$1 is not installed. Please install it to continue."
        exit 1
    fi
}

# Function to check if a Python package is installed
is_python_package_installed() {
    python3 -c "import pkg_resources; exit(not pkg_resources.require('$1'))" 2>/dev/null
    return $?
}

# Function to check if a Python package is installed in Wine
is_wine_python_package_installed() {
    $wine_executable python -c "import pkg_resources; exit(not pkg_resources.require('$1'))" 2>/dev/null
    return $?
}

# Check for necessary dependencies
check_dependency "curl"
check_dependency "$wine_executable"

# Install Mono if not present
if [ ! -e "/config/.wine/drive_c/windows/mono" ]; then
    show_message "[1/7] Downloading and installing Mono..."
    curl -o /config/.wine/drive_c/mono.msi $mono_url
    WINEDLLOVERRIDES=mscoree=d $wine_executable msiexec /i /config/.wine/drive_c/mono.msi /qn
    rm /config/.wine/drive_c/mono.msi
    show_message "[1/7] Mono installed."
else
    show_message "[1/7] Mono is already installed."
fi

# Check if MetaTrader 5 is already installed
if [ -e "$mt5file" ]; then
    show_message "[2/7] File $mt5file already exists."
else
    show_message "[2/7] File $mt5file is not installed. Installing..."

    # Set Windows 10 mode in Wine and download and install MT5
    $wine_executable reg add "HKEY_CURRENT_USER\\Software\\Wine" /v Version /t REG_SZ /d "win10" /f
    show_message "[3/7] Downloading MT5 installer..."
    curl -o /config/.wine/drive_c/mt5setup.exe $mt5setup_url
    show_message "[3/7] Installing MetaTrader 5..."
    $wine_executable "/config/.wine/drive_c/mt5setup.exe" "/auto" &
    wait
    rm -f /config/.wine/drive_c/mt5setup.exe
fi

# Function to enable AutoTrading in MT5
enable_autotrading() {
    local mt5_config_dir="/config/.wine/drive_c/Program Files/MetaTrader 5/config"
    local common_ini="$mt5_config_dir/common.ini"

    # Create config directory if it doesn't exist
    mkdir -p "$mt5_config_dir"

    # Create or update common.ini to enable AutoTrading
    if [ -f "$common_ini" ]; then
        # Update existing file
        if grep -q "AutoTrading=" "$common_ini"; then
            sed -i 's/AutoTrading=.*/AutoTrading=1/' "$common_ini"
        else
            echo "AutoTrading=1" >> "$common_ini"
        fi
    else
        # Create new file
        cat > "$common_ini" << 'INIEOF'
[Common]
AutoTrading=1
INIEOF
    fi

    show_message "AutoTrading enabled in config"
}

# Function to enable AutoTrading via xdotool (backup method)
enable_autotrading_xdotool() {
    local max_wait=60
    local waited=0

    # Wait for MT5 window to appear
    export DISPLAY=:1

    if ! command -v xdotool &> /dev/null; then
        show_message "xdotool not available, skipping keyboard AutoTrading toggle"
        return 1
    fi

    show_message "Waiting for MT5 window to appear..."

    # Wait for MT5 window
    while [ $waited -lt $max_wait ]; do
        # Try to find MT5 window
        MT5_WINDOW=$(xdotool search --name "MetaTrader 5" 2>/dev/null | head -1)
        if [ -n "$MT5_WINDOW" ]; then
            show_message "MT5 window found (ID: $MT5_WINDOW)"

            # Give the window time to be fully loaded
            sleep 5

            # Focus the window and send Ctrl+E
            xdotool windowactivate --sync "$MT5_WINDOW" 2>/dev/null || true
            sleep 1
            xdotool key --window "$MT5_WINDOW" ctrl+e 2>/dev/null || xdotool key ctrl+e
            sleep 2

            show_message "AutoTrading enabled via xdotool"
            return 0
        fi

        sleep 3
        waited=$((waited + 3))
    done

    show_message "Warning: MT5 window not found after $max_wait seconds, trying blind key press"
    # Try sending the key anyway
    xdotool key ctrl+e 2>/dev/null || true
}

# Function to wait for MT5 to be fully connected
wait_for_mt5_ready() {
    local max_wait=120  # Maximum wait time in seconds
    local check_interval=5
    local waited=0

    show_message "Waiting for MT5 to fully initialize..."

    while [ $waited -lt $max_wait ]; do
        # Check if terminal64.exe is running
        if pgrep -f "terminal64.exe" > /dev/null 2>&1; then
            # Give MT5 additional time to connect to broker
            sleep 10
            show_message "MT5 terminal detected and appears ready"
            return 0
        fi

        sleep $check_interval
        waited=$((waited + check_interval))
        show_message "Still waiting for MT5... ($waited/$max_wait seconds)"
    done

    show_message "Warning: MT5 may not be fully ready after $max_wait seconds"
    return 1
}

# Recheck if MetaTrader 5 is installed
if [ -e "$mt5file" ]; then
    show_message "[4/7] File $mt5file is installed. Running MT5..."

    # Enable AutoTrading before starting MT5
    enable_autotrading

    # Build command line options
    MT5_OPTS=$(build_mt5_options)
    show_message "Starting MT5 with options: [credentials hidden]"

    # Start MT5 with credentials from environment
    # Using bash -c to properly handle special characters in passwords
    if [ -n "${MT5_LOGIN:-}" ]; then
        # Use individual variables for better handling of special characters
        MT5_ARGS=("$mt5file")
        [ "${MT5_PORTABLE:-}" = "true" ] && MT5_ARGS+=("/portable")
        [ -n "$MT5_LOGIN" ] && MT5_ARGS+=("/login:$MT5_LOGIN")
        [ -n "$MT5_PASSWORD" ] && MT5_ARGS+=("/password:$MT5_PASSWORD")
        [ -n "$MT5_SERVER" ] && MT5_ARGS+=("/server:$MT5_SERVER")

        $wine_executable "${MT5_ARGS[@]}" &
    else
        # Fall back to MT5_CMD_OPTIONS - write to file to avoid shell interpretation issues
        echo "$MT5_OPTS" > /tmp/mt5_opts.txt
        $wine_executable "$mt5file" $(cat /tmp/mt5_opts.txt) &
    fi
    MT5_PID=$!

    # Wait for MT5 to be ready
    sleep 15  # Initial delay for Wine to start
    wait_for_mt5_ready

    # Enable AutoTrading via xdotool after MT5 is ready
    show_message "Enabling AutoTrading via keyboard shortcut..."
    enable_autotrading_xdotool &
else
    show_message "[4/7] File $mt5file is not installed. MT5 cannot be run."
fi


# Install Python in Wine if not present
if ! $wine_executable python --version 2>/dev/null; then
    show_message "[5/7] Installing Python in Wine..."
    curl -L $python_url -o /tmp/python-installer.exe
    $wine_executable /tmp/python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    rm /tmp/python-installer.exe
    show_message "[5/7] Python installed in Wine."
else
    show_message "[5/7] Python is already installed in Wine."
fi

# Upgrade pip and install required packages
show_message "[6/7] Installing Python libraries"
$wine_executable python -m pip install --upgrade --no-cache-dir pip
# Install MetaTrader5 library in Windows if not installed
show_message "[6/7] Installing MetaTrader5 library in Windows"
if ! is_wine_python_package_installed "MetaTrader5==$metatrader_version"; then
    $wine_executable python -m pip install --no-cache-dir MetaTrader5==$metatrader_version
fi
# Install mt5linux library in Windows if not installed
show_message "[6/7] Checking and installing mt5linux library in Windows if necessary"
if ! is_wine_python_package_installed "mt5linux"; then
    $wine_executable python -m pip install --no-cache-dir "mt5linux>=0.1.9"
fi

# Install python-dateutil if needed (datetime is built-in, but dateutil adds features)
if ! is_wine_python_package_installed "python-dateutil"; then
    show_message "[6/7] Installing python-dateutil library in Windows"
    $wine_executable python -m pip install --no-cache-dir python-dateutil
fi

# Install mt5linux library in Linux if not installed
show_message "[6/7] Checking and installing mt5linux library in Linux if necessary"
if ! is_python_package_installed "mt5linux"; then
    pip install --break-system-packages --no-cache-dir --no-deps mt5linux && \
    pip install --break-system-packages --no-cache-dir rpyc plumbum numpy
fi

# Install pyxdg library in Linux if not installed
show_message "[6/7] Checking and installing pyxdg library in Linux if necessary"
if ! is_python_package_installed "pyxdg"; then
    pip install --break-system-packages --no-cache-dir pyxdg
fi

# Wait for MT5 to be fully stable before starting RPyC server
show_message "[7/7] Waiting for MT5 to stabilize before starting server..."
sleep 30

# Function to test MT5 IPC connection
test_mt5_connection() {
    show_message "Testing MT5 IPC connection..."
    python3 << 'PYEOF'
import sys
try:
    from mt5linux import MetaTrader5
    mt5 = MetaTrader5()
    if mt5.initialize():
        info = mt5.account_info()
        if info:
            print(f"MT5 connection OK - Account: {info.login}, Balance: {info.balance}")
            mt5.shutdown()
            sys.exit(0)
        else:
            print("MT5 initialized but no account info")
    else:
        error = mt5.last_error()
        print(f"MT5 initialization failed: {error}")
except Exception as e:
    print(f"Error: {e}")
sys.exit(1)
PYEOF
    return $?
}

# Start the MT5 server on Linux
show_message "[7/7] Starting the mt5linux server..."
python3 -m mt5linux --host 0.0.0.0 -p $mt5server_port -w $wine_executable python.exe &
SERVER_PID=$!

# Give the server time to start
sleep 10

# Check if the server is running
if ss -tuln | grep ":$mt5server_port" > /dev/null; then
    show_message "[7/7] The mt5linux server is running on port $mt5server_port."

    # Test the connection
    max_test_attempts=6
    test_attempt=0
    while [ $test_attempt -lt $max_test_attempts ]; do
        if test_mt5_connection; then
            show_message "[7/7] MT5 IPC connection verified successfully!"
            break
        fi
        test_attempt=$((test_attempt + 1))
        show_message "MT5 IPC test attempt $test_attempt/$max_test_attempts failed, retrying in 10 seconds..."
        sleep 10
    done

    if [ $test_attempt -eq $max_test_attempts ]; then
        show_message "[7/7] Warning: MT5 IPC connection tests failed, but server is running. Connection may work later."
    fi
else
    show_message "[7/7] Failed to start the mt5linux server on port $mt5server_port."
fi

# Keep container running
show_message "Container initialization complete."
