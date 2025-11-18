"""
Configuration deployment utilities.

This example demonstrates how to create APIs that:
1. Access environment configuration (env.user_env)
2. Interact with devices
3. Store results in variables
"""

import os

from lib.services import env, logger


# pylint: disable=too-many-locals
def deploy_config(executor, params):
    """
    Deploy configuration using environment-specific values.

    Parameters (accessed via params object):
        params.config_template (str): Path to config template [-config_template]
        params.result_var (str): Variable to store result (default: deploy_status) [-result_var]

    Example:
        [FGT_A]
        deploy_config -config_template "configs/base.conf" -result_var status
        check_var -name status -pattern "success.*True" -for 801830
    """
    config_template = params.config_template
    result_var = params.get("result_var", "deploy_status")

    # Access environment config (FosConfigParser)
    config = env.user_env

    # Get values from config sections with fallbacks
    mgmt_ip = (
        config.get("GLOBAL", "MGMT_IP")
        if config.has_option("GLOBAL", "MGMT_IP")
        else "192.168.1.1"
    )
    vdom = (
        config.get("GLOBAL", "VDOM") if config.has_option("GLOBAL", "VDOM") else "root"
    )
    site_name = (
        config.get("GLOBAL", "SITE_NAME")
        if config.has_option("GLOBAL", "SITE_NAME")
        else "default"
    )

    # Load template file
    workspace = getattr(executor, "workspace", "")
    template_path = os.path.join(workspace, config_template)

    try:
        with open(template_path, "r") as f:
            config_text = f.read()
    except FileNotFoundError:
        error_result = {
            "success": False,
            "error": f"Template file not found: {template_path}",
        }
        env.add_var(result_var, error_result)
        logger.error("deploy_config: Template not found: %s", template_path)
        return error_result

    # Substitute environment variables
    config_text = config_text.replace("{mgmt_ip}", mgmt_ip)
    config_text = config_text.replace("{vdom}", vdom)
    config_text = config_text.replace("{site_name}", site_name)

    # Deploy to current device
    try:
        output = executor.cur_device.send(config_text)

        # Check for errors in output
        success = "error" not in output.lower() and "invalid" not in output.lower()

        result = {
            "success": success,
            "site": site_name,
            "vdom": vdom,
            "output": output[:200],  # Truncate output
        }

        # Store result using env service
        env.add_var(result_var, result)

        status = "SUCCESS" if success else "FAILED"
        logger.info("deploy_config: %s for site '%s'", status, site_name)
        return result

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        env.add_var(result_var, error_result)
        logger.error("deploy_config: Exception occurred: %s", e)
        return error_result
