#!/bin/bash
# Test script to reproduce the sed issue

# Create a test env file
echo "TEST_KEY=oldvalue" > test.env

# Define the set_env_kv function
set_env_kv() {
  local key="$1" value="$2" file="$3"
  echo "Testing: key='$key', value='$value'"
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    echo "Running: sed -i.bak \"s|^${key}=.*|${key}=${value}|\" \"$file\""
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

# Test with normal value
echo "=== Test 1: Normal value ==="
set_env_kv "TEST_KEY" "admin" "test.env"
cat test.env

# Test with value containing pipe
echo "=== Test 2: Value with pipe ==="
set_env_kv "TEST_KEY" "admin|pass" "test.env"
cat test.env

# Test with value containing special chars
echo "=== Test 3: Value with special chars ==="
set_env_kv "TEST_KEY" "admin&pass|test" "test.env"
cat test.env
