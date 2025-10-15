"""
Report API module.

Data collection and reporting APIs.
Module name 'report' becomes the category name.
"""

# pylint: disable=unused-argument


from lib.services import env


def report(executor, params):
    """
    Mark QAID for reporting with device info.

    Parameters (accessed via params object):
        params.qaid (str): Test case ID to report
    """
    qaid = params.qaid
    dut = executor.cur_device.dev_name if executor.cur_device else env.get_dut()
    executor.result_manager.add_report_qaid_and_dev_map(qaid, dut)


def collect_dev_info(executor, params):
    """
    Collect device information for test case.

    Parameters (accessed via params object):
        params.qaid (str): Test case ID [-for]
    """
    qaid = params.qaid
    device = executor.cur_device.dev_name
    # Access private method from executor
    device_info = executor.collect_dev_info_for_oriole(device)
    executor.result_manager.add_dev_info_requested_by_user(qaid, device_info)


def setlicense(executor, params):
    """
    Set license variable.

    Parameters (accessed via params object):
        params.lic_type (str): License type [-t]
        params.sub_type (str): License sub_type
        params.var_name (str): Variable name to store license [-to]
    """
    lic_type = params.lic_type
    sub_type = params.sub_type
    var_name = params.var_name
    env.set_license_var(lic_type, sub_type, var_name)
