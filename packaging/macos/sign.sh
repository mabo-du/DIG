#!/bin/bash
set -e

APP_PATH=$1
if [ -z "$APP_PATH" ]; then
    echo "Usage: $0 <path-to-app-or-dir>"
    exit 1
fi

if [ -z "$APPLE_SIGNING_IDENTITY" ]; then
    echo "APPLE_SIGNING_IDENTITY is not set, skipping codesign."
    exit 0
fi

echo "Signing $APP_PATH with identity $APPLE_SIGNING_IDENTITY"

# Sign inner libraries and frameworks
find "$APP_PATH" -type f -name "*.dylib" -o -name "*.so" | while read -r lib; do
    codesign --force --options runtime --sign "$APPLE_SIGNING_IDENTITY" "$lib"
done

# Sign the main executable/bundle
codesign --force --options runtime --entitlements packaging/macos/entitlements.plist --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"

echo "Signing complete."
