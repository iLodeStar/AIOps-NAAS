# Benthos v4 HTTP POST Quick Reference

## Problem
Benthos v4.27.0 does not support the `body:` parameter in HTTP processor configurations.

**Error Message:**
```
field body not recognised
```

## Solution Pattern

### ❌ OLD (Benthos v3 / Deprecated)
```yaml
- http:
    url: "http://api.example.com/endpoint"
    verb: POST
    headers:
      Content-Type: "application/json"
    body: |
      {
        "key": "value",
        "data": "${! json() }"
      }
```

### ✅ NEW (Benthos v4)
```yaml
# Step 1: Prepare the request body using mapping
- mapping: |
    root = {
      "key": "value",
      "data": this
    }

# Step 2: Send HTTP POST (uses message content as body)
- http:
    url: "http://api.example.com/endpoint"
    verb: POST
    headers:
      Content-Type: "application/json"
```

## Key Differences

| Benthos v3 | Benthos v4 |
|------------|------------|
| `body:` parameter | Use `mapping` processor before `http` |
| `${! json() }` interpolation | `this` in mapping |
| `content().parse_json()` | `this` (already parsed) |
| `array[0]` | `array.index(0)` |
| `.parse_number()` | `.number()` |

## Common Patterns

### 1. Simple JSON POST
```yaml
- mapping: |
    root = {"message": "Hello", "timestamp": now()}
- http:
    url: "http://api/endpoint"
    verb: POST
    headers:
      Content-Type: "application/json"
```

### 2. POST with Dynamic Data
```yaml
- mapping: |
    root = {
      "user_id": this.user_id,
      "action": "login",
      "timestamp": now(),
      "metadata": this.metadata
    }
- http:
    url: "http://api/events"
    verb: POST
```

### 3. POST Plain Text (like SQL query)
```yaml
- mapping: |
    root = "SELECT * FROM table WHERE id = '" + this.id + "'"
- http:
    url: "http://clickhouse:8123/"
    verb: POST
    headers:
      Content-Type: "text/plain"
```

### 4. Using Variables from Branch
```yaml
- branch:
    request_map: |
      root = {
        "original_data": this,
        "extra_field": "value"
      }
    processors:
      - mapping: |
          root = {
            "api_key": "secret",
            "payload": this.original_data
          }
      - http:
          url: "http://api/endpoint"
          verb: POST
```

## Processing HTTP Response

### ❌ OLD
```yaml
- mapping: |
    root.result = content().parse_json().response
```

### ✅ NEW
```yaml
- mapping: |
    root.result = this.response  # Already parsed if valid JSON
```

## Array and String Operations

### Array Access
```yaml
# ❌ OLD
this.array[0]

# ✅ NEW
this.array.index(0)
```

### Array with Null Check
```yaml
let first_item = if this.array != null && this.array.length() > 0 {
  this.array.index(0)
} else {
  "default_value"
}
```

### String to Number
```yaml
# ❌ OLD
this.value.parse_number()

# ✅ NEW
this.value.number()
this.value.number().catch(0)  # With fallback
```

## Testing Your Config

### Quick Validation
```bash
docker run --rm -v "$(pwd)/config.yaml:/config.yaml:ro" \
  jeffail/benthos:latest lint /config.yaml
```

### Expected Output
```
# Success (no output, exit code 0)

# Error
/config.yaml(10,5) field body not recognised
```

## Migration Checklist

- [ ] Find all `- http:` processors with `verb: POST`
- [ ] Check if they have a `body:` parameter
- [ ] Add `- mapping:` processor **before** each `http` processor
- [ ] Move `body:` content to the `mapping` processor
- [ ] Replace `${! ... }` interpolations with Bloblang syntax
- [ ] Update `content()` references to `this`
- [ ] Update array indexing from `[n]` to `.index(n)`
- [ ] Update `.parse_number()` to `.number()`
- [ ] Test with `benthos lint`

## Common Errors and Fixes

### Error: `field body not recognised`
**Fix:** Remove `body:` and add `mapping` processor before `http`

### Error: `wrong number of arguments, expected 0, got 1`
**Fix:** Change `content("variable")` to `this.variable`

### Error: `expected query, got: [0]`
**Fix:** Change `array[0]` to `array.index(0)`

### Error: `unrecognised method 'parse_number'`
**Fix:** Change `.parse_number()` to `.number()`

### Error: `field prefix not recognised` (in metrics)
**Fix:** Simplify metrics config:
```yaml
# ❌ OLD
metrics:
  prometheus:
    prefix: benthos_custom
  mapping: |
    root = this

# ✅ NEW
metrics:
  prometheus: {}
```

## Resources

- [Benthos v4 HTTP Processor](https://www.benthos.dev/docs/components/processors/http)
- [Benthos Mapping Processor](https://www.benthos.dev/docs/components/processors/mapping)
- [Bloblang Language Guide](https://www.benthos.dev/docs/guides/bloblang/about)
- [Migration Guide v3 to v4](https://www.benthos.dev/docs/guides/migration/v4)

## Example: Complete Before/After

### Before (Benthos v3)
```yaml
pipeline:
  processors:
    - http:
        url: "http://ollama:11434/api/generate"
        verb: POST
        headers:
          Content-Type: "application/json"
        body: |
          {
            "model": "llama2",
            "prompt": "Analyze: ${! json() }",
            "stream": false
          }
    - mapping: |
        root.result = content().parse_json().response
```

### After (Benthos v4)
```yaml
pipeline:
  processors:
    - mapping: |
        root = {
          "model": "llama2",
          "prompt": "Analyze: " + this.string(),
          "stream": false
        }
    - http:
        url: "http://ollama:11434/api/generate"
        verb: POST
        headers:
          Content-Type: "application/json"
    - mapping: |
        root.result = this.response
```

---

**Quick Tip:** Use `benthos lint` frequently during migration to catch syntax errors early!
