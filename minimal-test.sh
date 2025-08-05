#!/bin/bash

echo "Starting minimal test..."

echo "Test 1: Basic echo"
echo "This is a test"

echo "Test 2: Command check"
command -v git >/dev/null 2>&1
echo "Git check exit code: $?"

echo "Test 3: Function test"
test_function() {
    echo "Inside function"
    return 0
}

test_function
echo "Function completed"

echo "Test 4: Conditional"
if true; then
    echo "Conditional works"
fi

echo "Minimal test complete"