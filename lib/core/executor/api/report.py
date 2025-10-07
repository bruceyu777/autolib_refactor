"""
Report API module.

Data collection and reporting APIs.
Module name 'report' becomes the category name.
"""

# pylint: disable=unused-argument


from lib.services import env


def report(executor, parameters):
    """
    Mark QAID for reporting with device info.

    Parameters:
        0: qaid (str) - Test case ID
    """
    qaid = parameters[0]
    dut = executor.cur_device.dev_name if executor.cur_device else env.get_dut()
    executor.result_manager.add_report_qaid_and_dev_map(qaid, dut)


def collect_dev_info(executor, parameters):
    """
    Collect device information for test case.

    Parameters:
        0: qaid (str) - Test case ID
    """
    qaid = parameters[0]
    device = executor.cur_device.dev_name
    # Access private method from executor
    device_info = executor.collect_dev_info_for_oriole(device)
    executor.result_manager.add_dev_info_requested_by_user(qaid, device_info)


def setlicense(executor, parameters):
    """
    Set license variable.

    Parameters:
        0: lic_type (str) - License type
        1: file_name (str) - License file name
        2: var_name (str) - Variable name to store license
    """
    lic_type, file_name, var_name = parameters
    env.set_license_var(lic_type, file_name, var_name)
