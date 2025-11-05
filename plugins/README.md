# User-Defined API Plugins

This directory contains user-defined API plugins that extend the test automation framework.

## Directory Structure

```
plugins/
├── apis/              # User-defined API functions
│   ├── hostname.py    # Example: Extract hostname from output
│   └── deployment.py  # Example: Deploy config from templates
└── lib/               # Shared library code (optional)
    └── utils.py       # Common utilities
```

## Creating a New API Plugin

### Basic Pattern

1. Create a `.py` file in `plugins/apis/`
2. Define a function with signature: `def api_name(executor, params)`
3. Use `env.add_var()` to store results
4. Access environment config via `env.user_env`

### Simple Example

```python
# plugins/apis/my_api.py
"""
My custom API description.
"""

from lib.services import env, logger

def my_custom_api(executor, params):
    """
    API description.

    Parameters:
        params.input_param (str): Description [-input_param]
        params.output_var (str): Variable to store result [-output_var]

    Example:
        my_custom_api -input_param "value" -output_var result
    """
    # Get parameters
    input_param = params.input_param
    output_var = params.output_var

    # Access device output
    output = executor.last_output

    # Do processing...
    result = process(output, input_param)

    # Store result (IMPORTANT: use env.add_var!)
    env.add_var(output_var, result)

    logger.info(f"my_custom_api: Processed '{input_param}'")
    return result
```

### Accessing Context

Your API has access to:

- **`executor.last_output`**: Last command output from device
- **`executor.cur_device`**: Current device object
- **`executor.devices`**: All devices dict
- **`env.variables`**: Runtime variables (defaultdict)
- **`env.user_env`**: Parsed environment config (FosConfigParser)
- **`env.get_var(name)`**: Get a runtime variable
- **`env.add_var(name, value)`**: Set a runtime variable

### Environment Configuration Example

```python
def use_env_config(executor, params):
    """Access values from environment file."""

    # Access parsed config (FosConfigParser)
    config = env.user_env

    # Get values from sections
    mgmt_ip = config.get("GLOBAL", "MGMT_IP")
    device_host = config.get("FGT_A", "HOST")

    # Check if option exists
    if config.has_option("GLOBAL", "SITE_NAME"):
        site = config.get("GLOBAL", "SITE_NAME")

    # Store in variables
    env.add_var("site_name", site)
```

## Using Built-in APIs

### `exec_code` - Execute Code from Files

Execute Python, Bash, or other languages from external files:

```
# Execute Python script
exec_code -lang python -var hostname -file "scripts/extract_hostname.py"

# Execute Python with function call
exec_code -lang python -var result -file "plugins/lib/parser.py" -func "parse_output"

# Execute Python with function arguments
exec_code -lang python -var formatted -file "plugins/lib/format.py" -func "format_data" -args "json,pretty"

# Execute Bash script
exec_code -lang bash -var ip -file "scripts/get_ip.sh"
```

**Example code file** (`scripts/extract_hostname.py`):

```python
"""Extract hostname from device output."""
import re

# Access device output from context
output = context['last_output']

# Extract hostname using regex
match = re.search(r'Hostname:\s+(\w+)', output)
hostname = match.group(1) if match else 'unknown'

# Return value (stored in specified variable)
__result__ = hostname
```

**Context available in code files:**

- `context['last_output']` - Device output from last command
- `context['device']` - Current device object
- `context['devices']` - All devices dict
- `context['variables']` - Runtime variables dict
- `context['config']` - Environment config (FosConfigParser)
- `context['get_variable'](name)` - Helper to get variable
- `context['set_variable'](name, value)` - Helper to set variable
- `context['workspace']` - Workspace directory path
- `context['logger']` - Logger instance

**Important:** Always set `__result__` variable in Python code to return values.

### `check_var` - Validate Variable Contents

Check if a variable matches expected value:

```
# Exact match
check_var -name hostname -value "FGT-Branch-01" -for 801830

# Regex pattern
check_var -name hostname -pattern "FGT-.*" -for 801831

# Contains substring
check_var -name status -contains "success" -for 801832

# Inverse logic (fail if matched)
check_var -name error_log -contains "ERROR" -for 801833 -fail match
```

## Complete Example

### Test Script

```
# test_script.txt

[FGT_A]
get system status

# Use custom API
extract_hostname -var hostname

# Validate with check_var
check_var -name hostname -pattern "FGT-.*" -for 801830

# Use Python file for complex logic
exec_code -lang python -var admin_url -file "scripts/build_admin_url.py"

check_var -name admin_url -contains "https://" -for 801831

# Deploy configuration
deploy_config -config_template "configs/base.conf" -result_var deploy_status

# Check deployment success
exec_code -lang python -var deploy_ok -file "scripts/check_deploy_status.py"

check_var -name deploy_ok -value "True" -for 801832

report 801830
report 801831
report 801832
```

### Supporting Code Files

`scripts/build_admin_url.py`:

```python
"""Build admin URL from environment configuration."""
config = context['config']
mgmt_ip = config.get('GLOBAL', 'MGMT_IP')
admin_port = config.get('GLOBAL', 'ADMIN_PORT', fallback='443')
__result__ = f'https://{mgmt_ip}:{admin_port}'
```

`scripts/check_deploy_status.py`:

```python
"""Check if deployment was successful."""
status = context['variables'].get('deploy_status', {})
__result__ = status.get('success', False)
```

## Important Notes

### ✅ DO:

- Use `env.add_var(name, value)` to set variables
- Use `env.get_var(name)` to get variables
- Access `env.user_env` for environment config
- Follow the `(executor, params)` signature pattern
- Document your API with docstrings
- **Use file-based code** with `exec_code` (organize in `scripts/` directory)
- **Set `__result__`** in Python code files to return values
- **Test code files independently** before using in scripts

### ❌ DON'T:

- ~~Use `executor.variables`~~ (doesn't exist!)
- ~~Use `task.env`~~ (use `env.user_env` instead)
- ~~Modify `executor` internal state directly~~
- ~~Forget to log with `logger.info()`~~
- ~~Use inline `-code` parameter~~ (not supported - use `-file` instead)

## Auto-Discovery

Your APIs are automatically discovered when placed in `plugins/apis/`. No registration required!

All public functions (not starting with `_`) are automatically registered as APIs.

## Questions?

See existing examples:

- `plugins/apis/hostname.py` - Simple extraction
- `plugins/apis/deployment.py` - Environment-aware deployment
