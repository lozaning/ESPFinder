#!/bin/bash

echo "🔍 Debug Installation Script"
echo "=============================="

echo "Testing basic commands..."

echo "Step 1: Testing git check"
if command -v git >/dev/null 2>&1; then
    echo "✅ git is installed"
else
    echo "❌ git is not installed"
fi

echo "Step 2: Testing docker check"
if command -v docker >/dev/null 2>&1; then
    echo "✅ docker is installed"
else
    echo "❌ docker is not installed"
fi

echo "Step 3: Testing OSTYPE"
echo "OSTYPE: $OSTYPE"

echo "Step 4: Testing HOME"
echo "HOME: $HOME"

echo "Debug complete!"