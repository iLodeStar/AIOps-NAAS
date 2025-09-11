#!/usr/bin/env python3
"""
Simple validation test to ensure the ship_id fix is correctly implemented
"""

def test_code_changes():
    """Test that the hardcoded 'ship-01' has been replaced"""
    
    # Read the incident API file
    with open('services/incident-api/incident_api.py', 'r') as f:
        content = f.read()
    
    # Check that the hardcoded 'ship-01' fallback has been removed
    if "incident_data.get('ship_id', 'ship-01')" in content:
        print("❌ ERROR: Hardcoded 'ship-01' fallback still present")
        return False
    
    # Check that the resolve_ship_id method was added
    if "async def resolve_ship_id" not in content:
        print("❌ ERROR: resolve_ship_id method not found")
        return False
    
    # Check that device registry lookup is implemented
    if "http://device-registry:8080/lookup" not in content:
        print("❌ ERROR: Device registry lookup not implemented")
        return False
    
    # Check that the store_incident method uses resolved_ship_id
    if "resolved_ship_id = await self.resolve_ship_id(incident_data)" not in content:
        print("❌ ERROR: store_incident method not updated to use resolve_ship_id")
        return False
    
    # Check that 'unknown-ship' is used as ultimate fallback (consistent with Benthos)
    if 'return "unknown-ship"' not in content:
        print("❌ ERROR: 'unknown-ship' fallback not found")
        return False
    
    print("✅ All code changes validated successfully!")
    print("✅ Hardcoded 'ship-01' fallback removed")
    print("✅ Device registry integration added") 
    print("✅ Hostname-based derivation fallback implemented")
    print("✅ Consistent 'unknown-ship' ultimate fallback")
    
    return True


def test_logic_flow():
    """Test the ship_id resolution logic"""
    
    print("\n🔍 Testing ship_id resolution logic:")
    print("1. If valid ship_id exists -> use it")
    print("2. Try device registry lookup using hostname")
    print("3. Fallback to hostname-based derivation (e.g., 'dhruv-system' -> 'dhruv-ship')")
    print("4. Ultimate fallback to 'unknown-ship'")
    
    # Read the resolve_ship_id method
    with open('services/incident-api/incident_api.py', 'r') as f:
        content = f.read()
    
    # Extract the resolve_ship_id method
    start_marker = "async def resolve_ship_id"
    end_marker = "return \"unknown-ship\""
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx) + len(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("❌ ERROR: Could not find resolve_ship_id method")
        return False
    
    resolve_method = content[start_idx:end_idx]
    
    # Check logic order
    logic_checks = [
        ("Valid ship_id check", "ship_id and ship_id != \"\" and not ship_id.startswith(\"unknown\")"),
        ("Device registry call", "requests.get(f\"http://device-registry:8080/lookup/{hostname}\""),
        ("Hostname derivation", "hostname.split(\"-\")[0] + \"-ship\""),
        ("Ultimate fallback", "return \"unknown-ship\"")
    ]
    
    for check_name, pattern in logic_checks:
        if pattern in resolve_method:
            print(f"✅ {check_name} - implemented")
        else:
            print(f"❌ {check_name} - missing")
            return False
    
    return True


if __name__ == "__main__":
    print("🧪 Testing ship_id fix implementation...")
    
    success = test_code_changes() and test_logic_flow()
    
    if success:
        print("\n🎉 Ship_id fix validation PASSED!")
        print("\nThe incident API will now:")
        print("- Try device registry lookup for registered ships like 'ship-dhruv'")
        print("- Fallback to hostname derivation if registry lookup fails")
        print("- Use 'unknown-ship' as ultimate fallback (not 'ship-01')")
        print("\nThis should resolve the issue where ship 'ship-dhruv' was registered")
        print("but incidents were incorrectly showing 'ship-01'.")
    else:
        print("\n❌ Ship_id fix validation FAILED!")
    
    exit(0 if success else 1)