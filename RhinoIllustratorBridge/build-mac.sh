#!/bin/bash
# build-mac.sh
# Builds the RhinoIllustratorBridge plugin and packages it as a .yak and .macrhi file for macOS.

set -e

# Configuration
CONFIGURATION="Release"
YAK_PATH="/Applications/Rhino 8.app/Contents/Resources/bin/yak"

# Ensure we're in the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PROJECT_FILE="RhinoIllustratorBridge.csproj"

echo "=================================================="
echo "  Rhino-Illustrator Sync - macOS Packager"
echo "=================================================="
echo ""

# Step 1: Build the C# project
echo "[1/5] Building project ($CONFIGURATION)..."
dotnet build "$PROJECT_FILE" -c "$CONFIGURATION" --nologo
echo "  Build succeeded."
echo ""

# Step 2: Prepare staging directory for Yak package
BUILD_OUTPUT="bin/$CONFIGURATION/net7.0"
STAGING_DIR="yak-staging"
NET7_DIR="$STAGING_DIR/net7.0"

echo "[2/5] Preparing staging directory..."
rm -rf "$STAGING_DIR"
mkdir -p "$NET7_DIR"

# Copy built files, excluding RhinoCommon and Eto references (provided by Rhino runtime)
for file in "$BUILD_OUTPUT"/*.{rhp,dll,pdb}; do
    # Check if files exist before trying to copy
    [ -e "$file" ] || continue
    filename=$(basename "$file")
    if [[ "$filename" =~ ^(RhinoCommon|Eto\.) ]]; then
        continue
    fi
    cp "$file" "$NET7_DIR/"
    echo "  Copied: $filename"
done

# Copy manifest.yml
if [ -f "manifest.yml" ]; then
    cp "manifest.yml" "$STAGING_DIR/"
    echo "  Copied: manifest.yml"
else
    echo "  Error: manifest.yml not found!"
    exit 1
fi

# Copy icon
ICON_SRC="Resources/sync_icon.png"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$STAGING_DIR/icon.png"
    echo "  Copied: icon.png"
else
    echo "  Warning: sync_icon.png not found at $ICON_SRC"
fi
echo "  Staging complete."
echo ""

# Step 3: Build the Yak package
echo "[3/5] Building Yak package..."
if [ -f "$YAK_PATH" ]; then
    cd "$STAGING_DIR"
    "$YAK_PATH" build
    cd ..
    
    # Move the resulting .yak file to the project root
    YAK_FILE=$(find "$STAGING_DIR" -maxdepth 1 -name "*.yak" | head -n 1)
    if [ -n "$YAK_FILE" ]; then
        mv "$YAK_FILE" ./
        echo "  Yak Package created: $(basename "$YAK_FILE")"
    else
        echo "  Error: Yak build did not generate a .yak file."
        exit 1
    fi
else
    echo "  Yak CLI not found at: $YAK_PATH"
    echo "  Skipping Yak packaging."
fi
echo ""

# Step 4: Package the .macrhi installer
echo "[4/5] Packaging .macrhi installer..."
MACRHI_STAGING="macrhi-staging"
MACRHI_FOLDER="$MACRHI_STAGING/RhinoIllustratorBridge.rhp"

rm -rf "$MACRHI_STAGING"
mkdir -p "$MACRHI_FOLDER"

# Copy files that are required in the plugin directory
cp -R "$NET7_DIR"/* "$MACRHI_FOLDER/"

# Include RUI file if it exists in the build output (or in dist/mac)
if [ -f "../dist/mac/RhinoIllustratorBridge.rui" ]; then
    cp "../dist/mac/RhinoIllustratorBridge.rui" "$MACRHI_FOLDER/"
    echo "  Bundled: RhinoIllustratorBridge.rui"
fi

# Zip the directory and rename it to .macrhi
cd "$MACRHI_STAGING"
zip -q -r ../RhinoIllustratorBridge.macrhi RhinoIllustratorBridge.rhp
cd ..

rm -rf "$MACRHI_STAGING"
echo "  Mac Rhino Installer (.macrhi) created: RhinoIllustratorBridge.macrhi"
echo ""

# Step 5: Update the dist/mac and dist/windows files
echo "[5/5] Updating files in dist/mac and dist/windows..."
DIST_MAC_DIR="../dist/mac"
if [ -d "$DIST_MAC_DIR" ]; then
    cp "$BUILD_OUTPUT/RhinoIllustratorBridge.rhp" "$DIST_MAC_DIR/"
    echo "  Updated dist/mac/RhinoIllustratorBridge.rhp"
    
    # Copy the newly built .macrhi package to dist/mac as well for easy access
    cp "RhinoIllustratorBridge.macrhi" "$DIST_MAC_DIR/"
    echo "  Copied dist/mac/RhinoIllustratorBridge.macrhi"
else
    echo "  Warning: dist/mac directory not found!"
fi

DIST_WIN_DIR="../dist/windows"
if [ -d "$DIST_WIN_DIR" ]; then
    cp "$BUILD_OUTPUT/RhinoIllustratorBridge.rhp" "$DIST_WIN_DIR/"
    echo "  Updated dist/windows/RhinoIllustratorBridge.rhp"
else
    echo "  Warning: dist/windows directory not found!"
fi

echo ""
echo "Summary:"
echo "  Staging dir:  $STAGING_DIR"
echo "  Yak Package:  ./RhinoIllustratorBridge.*.yak (for Package Manager)"
echo "  Mac Installer: ./RhinoIllustratorBridge.macrhi (Double-click to install)"
echo "  Raw Plugin:    dist/mac/RhinoIllustratorBridge.rhp (Manual load)"
echo ""
echo "Done!"
