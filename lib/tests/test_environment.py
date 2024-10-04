from collections import namedtuple

from lib.services.environment import Environment


def test_add_variable():
    env = Environment()
    env.add_var("sn", "13333")
    assert env.get_var("sn") == "13333"


def test_get_vm_type():
    env = Environment()
    args = namedtuple("args", ["env", "script"])
    args.env = "lib/testcases/env/env.vm04.conf"
    args.script = "lib/testcases/scripts/if_cmd.txt"
    env.init_env(args)
    dev_cfg = env.get_dev_cfg("KVM_3")

    print(dev_cfg.get("non_sriov", "no") == "yes")
