#!/bin/bash
set -e

APP_NAME="OverLLM"
APP_VERSION="1.0.0"
DMG_NAME="OverLLM-RL-GA-DAG-${APP_VERSION}"
BUILD_DIR="build"
APP_DIR="${BUILD_DIR}/${APP_NAME}.app"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"
DMG_TEMP_DIR="${BUILD_DIR}/dmg"

echo "🚀 Building OverLLM RL-GA-DAG Vector Search System..."

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

echo "📦 Building C++ inference engine..."
cd cpp
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(sysctl -n hw.ncpu)
cd ../..

echo "📦 Building Rust telemetry daemon..."
cd rust
cargo build --release
cd ..

echo "📦 Building Go orchestrator..."
cd go
go build -o ../${BUILD_DIR}/overllm-agent ./cmd/overllm-agent
cd ..

echo "📦 Building React UI..."
cd ui
npm install
npm run build
cd ..

echo "📁 Creating macOS .app bundle..."
rm -rf "${APP_DIR}"
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

echo "📋 Copying binaries..."
cp cpp/build/overllm_inference "${RESOURCES_DIR}/"
cp rust/target/release/overllm-telemetry "${RESOURCES_DIR}/"
cp ${BUILD_DIR}/overllm-agent "${RESOURCES_DIR}/" 2>/dev/null || cp overllm-agent "${RESOURCES_DIR}/"
mkdir -p "${RESOURCES_DIR}/ui"
cp -r ui/dist/* "${RESOURCES_DIR}/ui/"

echo "📋 Copying models and data..."
mkdir -p "${RESOURCES_DIR}/models"
mkdir -p "${RESOURCES_DIR}/data"
if [ -d "models" ]; then
    cp -r models/* "${RESOURCES_DIR}/models/" 2>/dev/null || true
fi
cp vocab.txt "${RESOURCES_DIR}/" 2>/dev/null || true

echo "📝 Creating Info.plist..."
cat > "${CONTENTS_DIR}/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleExecutable</key>
    <string>OverLLM</string>
    <key>CFBundleIdentifier</key>
    <string>com.overllm.rlgadag</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${APP_VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${APP_VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
EOF

echo "🔧 Creating native launcher..."
cat > /tmp/launcher.c << 'EOF'
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>

int main() {
    // Change to Resources directory (relative to MacOS)
    chdir("../Resources");
    
    // Start the agent
    pid_t pid = fork();
    if (pid == 0) {
        execl("./overllm-agent", "./overllm-agent", NULL);
        exit(1);
    }

    sleep(2);

    // Open browser
    pid_t ui_pid = fork();
    if (ui_pid == 0) {
        execlp("open", "open", "http://localhost:7749", NULL);
        exit(1);
    }

    int status;
    waitpid(pid, &status, 0);

    return 0;
}
EOF

clang -o "${MACOS_DIR}/OverLLM" /tmp/launcher.c -arch arm64
rm /tmp/launcher.c

echo "💿 Skipping DMG creation - testing app bundle directly..."
# rm -rf "${DMG_TEMP_DIR}"
# mkdir -p "${DMG_TEMP_DIR}"
# cp -R "${APP_DIR}" "${DMG_TEMP_DIR}/"
# ln -s /Applications "${DMG_TEMP_DIR}/Applications"
# hdiutil create -volname "${APP_NAME}" -srcfolder "${DMG_TEMP_DIR}" -ov -format UDRW "${BUILD_DIR}/${DMG_NAME}.dmg" >/dev/null
# MOUNT_DIR="/Volumes/${APP_NAME}"
# hdiutil attach "${BUILD_DIR}/${DMG_NAME}.dmg" -readwrite -mountpoint "${MOUNT_DIR}" >/dev/null
# hdiutil detach "${MOUNT_DIR}" >/dev/null
# hdiutil convert "${BUILD_DIR}/${DMG_NAME}.dmg" -format UDZO -imagekey zlib-level=9 -o "${BUILD_DIR}/${DMG_NAME}-final.dmg" >/dev/null
# mv "${BUILD_DIR}/${DMG_NAME}-final.dmg" "${BUILD_DIR}/${DMG_NAME}.dmg"
# rm -rf "${DMG_TEMP_DIR}"

echo "✅ Build complete!"
echo "📦 App bundle created: ${APP_DIR}"
echo "Test by running: open ${APP_DIR}"
