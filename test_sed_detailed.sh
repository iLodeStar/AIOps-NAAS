#!/bin/bash
# Test script to find the exact issue

# Create a test env file
echo "TEST_KEY=oldvalue" > test.env

# Define the set_env_kv function
set_env_kv() {
  local key="$1" value="$2" file="$3"
  echo "Testing: key='$key', value='$value' (length: ${#value})"
  echo "Hex dump of value:"
  printf '%s' "$value" | od -tx1
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    echo "Running: sed -i.bak \"s|^${key}=.*|${key}=${value}|\" \"$file\""
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$file" 2>&1
  else
    echo "${key}=${value}" >> "$file"
  fi
}

# Test with different problematic values
echo "=== Test 1: Value with newline ==="
set_env_kv "TEST_KEY" $'admin\ntest' "test.env"

echo -e "\n=== Test 2: Value with carriage return ==="  
set_env_kv "TEST_KEY" $'admin\rtest' "test.env"

echo -e "\n=== Test 3: Empty value ==="
set_env_kv "TEST_KEY" "" "test.env"

echo -e "\n=== Test 4: Value with forward slash ==="
set_env_kv "TEST_KEY" "admin/test" "test.env"
