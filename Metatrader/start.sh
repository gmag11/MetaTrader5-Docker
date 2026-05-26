#!/bin/bash

# Configuration variables
mt5file='/config/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe'
WINEPREFIX='/config/.wine'
WINEDEBUG='-all'
wine_executable="wine"
winearch="win64"
metatrader_version="5.0.36"
mt5server_port="8001"
MT5_CMD_OPTIONS="${MT5_CMD_OPTIONS:-}"
mono_url="https://dl.winehq.org/wine/wine-mono/10.3.0/wine-mono-10.3.0-x86.msi"
python_url="https://www.python.org/ftp/python/3.9.13/python-3.9.13.exe"
mt5setup_url="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
MAX_RETRIES=3
RETRY_DELAY=5

show_message() {
    echo "$1"
}

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "$1 is not installed. Please install it to continue."
        exit 1
    fi
}

is_python_package_installed() {
    python3 -c "import pkg_resources; exit(not pkg_resources.require('$1'))" 2>/dev/null
    return $?
}

is_wine_python_package_installed() {
    $wine_executable python -c "import pkg_resources; exit(not pkg_resources.require('$1'))" 2>/dev/null
    return $?
}

dismiss_dialogs() {
    if command -v xdotool &> /dev/null; then
        for _ in {1..10}; do
            window_id=$(xdotool search --name "mt5setup.exe" 2>/dev/null | head -1)
            if [ -n "$window_id" ]; then
                xdotool windowactivate "$window_id" 2>/dev/null
                xdotool key --window "$window_id" Return 2>/dev/null
                sleep 1
            else
                break
            fi
        done
    fi
}

check_dependency "curl"
check_dependency "$wine_executable"

if [ ! -d "/config/.wine" ]; then
    show_message "[0/7] Initializing Wine prefix..."
    wineboot -u 2>/dev/null || true
    wineserver -w 2>/dev/null || true
fi

# Install Mono if not present
if [ ! -e "/config/.wine/drive_c/windows/mono" ]; then
    show_message "[1/7] Downloading and installing Mono..."
    curl -sL -o /config/.wine/drive_c/mono.msi "$mono_url" || true
    if [ -f "/config/.wine/drive_c/mono.msi" ]; then
        WINEDLLOVERRIDES=mscoree=d $wine_executable msiexec /i /config/.wine/drive_c/mono.msi /qn 2>/dev/null || true
        rm -f /config/.wine/drive_c/mono.msi
        show_message "[1/7] Mono installed."
    else
        show_message "[1/7] Mono download failed, skipping."
    fi
else
    show_message "[1/7] Mono is already installed."
fi

# Check if MetaTrader 5 is already installed
if [ -e "$mt5file" ]; then
    show_message "[2/7] File $mt5file already exists."
else
    show_message "[2/7] File $mt5file is not installed. Installing..."

    # Set Windows 10 mode in Wine
    $wine_executable reg add "HKEY_CURRENT_USER\\Software\\Wine" /v Version /t REG_SZ /d "win10" /f 2>/dev/null

    show_message "[3/7] Downloading MT5 installer..."
    curl -sL -o /config/.wine/drive_c/mt5setup.exe "$mt5setup_url"
    if [ ! -f "/config/.wine/drive_c/mt5setup.exe" ]; then
        show_message "[3/7] ERROR: Failed to download MT5 installer."
        exit 1
    fi
    show_message "[3/7] Installing MetaTrader 5..."

    retry_count=0
    install_success=false
    while [ $retry_count -lt $MAX_RETRIES ] && [ "$install_success" = false ]; do
        DISPLAY=:99 xvfb-run -a "$wine_executable" "/config/.wine/drive_c/mt5setup.exe" "/auto" &
        installer_pid=$!

        sleep 10
        dismiss_dialogs

        wait "$installer_pid" 2>/dev/null || true
        sleep 2

        if [ -f "$mt5file" ]; then
            install_success=true
            show_message "[3/7] MetaTrader 5 installed successfully."
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $MAX_RETRIES ]; then
                show_message "[3/7] Installation attempt $retry_count failed, retrying in ${RETRY_DELAY}s..."
                dismiss_dialogs
                sleep "$RETRY_DELAY"
            fi
        fi
    done

    rm -f /config/.wine/drive_c/mt5setup.exe

    if [ "$install_success" = false ]; then
        show_message "[3/7] WARNING: MT5 installation may have failed after $MAX_RETRIES attempts."
    fi
fi

# Recheck if MetaTrader 5 is installed
if [ -e "$mt5file" ]; then
    show_message "[4/7] File $mt5file is installed. Running MT5..."
    $wine_executable "$mt5file" $MT5_CMD_OPTIONS &
else
    show_message "[4/7] File $mt5file is not installed. MT5 cannot be run."
fi

# Install Python in Wine if not present
if ! $wine_executable python --version 2>/dev/null; then
    show_message "[5/7] Installing Python in Wine..."
    curl -sL "$python_url" -o /tmp/python-installer.exe
    if [ -f "/tmp/python-installer.exe" ]; then
        $wine_executable /tmp/python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
        rm /tmp/python-installer.exe
        show_message "[5/7] Python installed in Wine."
    else
        show_message "[5/7] WARNING: Python download failed."
    fi
else
    show_message "[5/7] Python is already installed in Wine."
fi

# Upgrade pip and install required packages
show_message "[6/7] Installing Python libraries"
$wine_executable python -m pip install --upgrade --no-cache-dir pip 2>/dev/null || true
if ! is_wine_python_package_installed "MetaTrader5==$metatrader_version"; then
    $wine_executable python -m pip install --no-cache-dir MetaTrader5==$metatrader_version 2>/dev/null || true
fi
if ! is_wine_python_package_installed "mt5linux"; then
    $wine_executable python -m pip install --no-cache-dir "mt5linux>=0.1.9" 2>/dev/null || true
fi
if ! is_wine_python_package_installed "python-dateutil"; then
    $wine_executable python -m pip install --no-cache-dir python-dateutil 2>/dev/null || true
fi

# Install Linux Python packages
show_message "[6/7] Checking and installing Linux Python libraries"
if ! is_python_package_installed "mt5linux"; then
    pip install --break-system-packages --no-cache-dir --no-deps mt5linux 2>/dev/null || true
    pip install --break-system-packages --no-cache-dir rpyc plumbum numpy 2>/dev/null || true
fi
if ! is_python_package_installed "pyxdg"; then
    pip install --break-system-packages --no-cache-dir pyxdg 2>/dev/null || true
fi

# Start the authenticated mt5linux RPyC server
show_message "[7/7] Starting the mt5linux server..."
if [ -f "/Metatrader/server.py" ]; then
    python3 /Metatrader/server.py &
else
    python3 -m mt5linux --host 0.0.0.0 -p "$mt5server_port" &
fi

sleep 5

if ss -tuln | grep ":$mt5server_port" > /dev/null; then
    show_message "[7/7] The mt5linux server is running on port $mt5server_port."
    if [ -n "$MT5_AUTH_TOKEN" ]; then
        show_message "[7/7] Token authentication is ENABLED."
    fi
else
    show_message "[7/7] Failed to start the mt5linux server on port $mt5server_port."
fi
