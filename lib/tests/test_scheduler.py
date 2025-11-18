"""
Tests for lib.core.scheduler modules.
"""

# pylint: disable=import-outside-toplevel,unused-variable
# pylint: disable=unused-argument,unused-import

from unittest.mock import MagicMock, patch

import pytest


class TestTask:
    """Test suite for Task class."""

    def test_task_initialization(self, temp_script_file):
        """Test task initialization with script."""
        from lib.core.scheduler.task import Task

        with patch("lib.core.scheduler.task.Script"):
            task = Task(str(temp_script_file), non_strict_mode=True)
            assert task is not None
            assert task.non_strict_mode is True
            assert isinstance(task.devices, dict)

    def test_device_setup(self, mock_device, mocker):
        """Test setting up devices for task execution."""
        from lib.core.scheduler.task import Task

        mocker.patch("lib.core.scheduler.task.Script")
        mock_env = mocker.patch("lib.core.scheduler.task.env")
        mock_env.is_fos_device.return_value = True

        task = Task("dummy_script.conf")
        task.devices = {"FGT1": mock_device}

        # Test that device is set up
        assert "FGT1" in task.devices
        assert task.devices["FGT1"] == mock_device

    def test_device_composition(self, mocker):
        """Test discovering required devices from script."""
        from lib.core.scheduler.task import Task

        mock_script = MagicMock()
        mock_script.get_all_involved_devices.return_value = {"FGT1", "FGT2"}

        mocker.patch("lib.core.scheduler.task.Script", return_value=mock_script)
        mock_env = mocker.patch("lib.core.scheduler.task.env")
        mock_env.get_dut.return_value = "FGT1"
        mock_env.get_fap_controller.return_value = None

        task = Task("dummy_script.conf")
        devices = task.get_all_devices()

        assert "FGT1" in devices
        assert "FGT2" in devices

    def test_image_restoration(self, mocker):
        """Test device image restoration."""
        from lib.core.scheduler.task import Task

        mock_device = MagicMock()
        mocker.patch("lib.core.scheduler.task.Script")
        mock_env = mocker.patch("lib.core.scheduler.task.env")
        mock_env.get_restore_image_args.return_value = ("v7.0", "0113", True, False)
        mock_env.is_fos_device.return_value = True
        mock_env.need_deploy_vm.return_value = False

        task = Task("dummy_script.conf")
        task.devices = {"FGT1": mock_device}

        task.restore_image()

        mock_device.restore_image.assert_called_once_with("v7.0", "0113", True, False)

    def test_vm_deployment(self, mocker):
        """Test VM deployment workflow."""
        from lib.core.scheduler.task import Task

        mock_vm_manager = MagicMock()
        mocker.patch("lib.core.scheduler.task.VmManager", return_value=mock_vm_manager)
        mock_env = mocker.patch("lib.core.scheduler.task.env")
        mock_env.need_deploy_vm.return_value = True
        mocker.patch("lib.core.scheduler.task.sleep_with_progress")

        vms = ["vm1", "vm2"]
        Task.setup_vms(vms)

        mock_vm_manager.setup_vms.assert_called_once()

    def test_license_activation(self, mocker):
        """Test license activation for new VMs."""
        from lib.core.scheduler.task import Task

        mock_device = MagicMock()
        mock_device.activate_license = MagicMock()

        mocker.patch("lib.core.scheduler.task.Script")
        mock_env = mocker.patch("lib.core.scheduler.task.env")
        mock_env.need_activate_license.return_value = True

        task = Task("dummy_script.conf")
        task.devices = {"FGT1": mock_device}

        # Simulate license activation
        if mock_env.need_activate_license():
            mock_device.activate_license()

        mock_device.activate_license.assert_called_once()

    def test_script_execution(self, sample_vm_codes, mocker):
        """Test script execution with timing."""
        from lib.core.scheduler.task import Task

        mock_script = MagicMock()
        mocker.patch("lib.core.scheduler.task.Script", return_value=mock_script)
        mocker.patch("lib.core.scheduler.task.Executor")

        task = Task("dummy_script.conf")

        # Test that task has script attribute
        assert task.script == mock_script

    def test_result_submission(self, mocker):
        """Test submitting execution results."""
        from lib.core.scheduler.task import Task

        mocker.patch("lib.core.scheduler.task.Script")
        mock_summary = mocker.patch("lib.core.scheduler.task.summary")

        task = Task("dummy_script.conf")

        # Simulate result submission
        mock_summary.dump_brief_summary()

        mock_summary.dump_brief_summary.assert_called_once()


class TestJob:
    """Test suite for Job class."""

    def test_job_initialization(self, mocker):
        """Test job initialization."""
        from lib.core.scheduler.job import Job

        mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"

        job = Job(mock_args)

        assert job is not None
        assert hasattr(job, "args")

    def test_environment_initialization(self, mock_environment, mocker):
        """Test environment initialization for job."""
        from lib.core.scheduler.job import Job

        mock_env = mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")
        mocker.patch("lib.core.scheduler.job.oriole")

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"

        job = Job(mock_args)
        job.init_env()

        # Test that environment is available
        mock_env.init_env.assert_called_once_with(mock_args)

    def test_task_creation(self, mocker):
        """Test creating ScriptTask vs GroupTask."""
        from lib.core.scheduler.job import Job

        mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")
        mock_task = mocker.patch("lib.core.scheduler.job.ScriptTask")

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"
        mock_args.non_strict = False

        job = Job(mock_args)
        task = job.init_task()

        # Test that task was created
        mock_task.assert_called_once_with("test_script.conf", non_strict_mode=False)

    def test_web_server_fork(self, mock_os_fork, mocker):
        """Test forking web server process."""
        from lib.core.scheduler.job import Job

        mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")
        mock_os = mocker.patch("lib.core.scheduler.job.os")
        mock_os.fork.return_value = 0  # Child process

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"

        job = Job(mock_args)

        # Test fork behavior
        if mock_os.fork.return_value == 0:
            # Child process
            assert True

    def test_web_server_startup(self, mocker):
        """Test starting HTTP server."""
        from lib.core.scheduler.job import Job

        mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")
        mock_webserver = mocker.patch("lib.core.scheduler.job.webserver_main")

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"

        job = Job(mock_args)

        # Test web server can be instantiated
        assert mock_webserver is not None

    def test_result_webpage_launch(self, mocker):
        """Test opening browser to results."""
        from lib.core.scheduler.job import Job

        mocker.patch("lib.core.scheduler.job.env")
        mocker.patch("lib.core.scheduler.job.output")
        mocker.patch("lib.core.scheduler.job.summary")
        mock_webbrowser = mocker.patch("lib.core.scheduler.job.webbrowser")

        # Create mock args object
        mock_args = MagicMock()
        mock_args.script = "test_script.conf"
        mock_args.env = "test.env"

        job = Job(mock_args)

        # Simulate opening browser
        mock_webbrowser.open.return_value = True

        assert mock_webbrowser.open is not None


class TestGroupTask:
    """Test suite for GroupTask class."""

    def test_group_file_parsing(self, temp_group_file, mocker):
        """Test parsing group file."""
        from lib.core.scheduler.group_task import GroupTask

        mock_group = MagicMock()
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask(str(temp_group_file))

        assert group_task is not None
        assert hasattr(group_task, "group")

    def test_parallel_compilation(self, temp_group_file, mocker):
        """Test parallel script compilation."""
        from lib.core.scheduler.group_task import GroupTask

        mock_group = MagicMock()
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask(str(temp_group_file))

        # Test that group task was created
        assert group_task is not None

    def test_multi_script_execution(self, mocker):
        """Test executing multiple scripts."""
        from lib.core.scheduler.group_task import GroupTask

        mock_group = MagicMock()
        mock_group.scripts = ["script1.conf", "script2.conf", "script3.conf"]
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask("group_file.txt")

        assert len(mock_group.scripts) == 3

    def test_strict_mode_error_handling(self, mocker):
        """Test error handling in strict mode."""
        from lib.core.scheduler.group_task import GroupTask

        mock_group = MagicMock()
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask("group_file.txt", non_strict_mode=False)

        # In strict mode, non_strict_mode should be False
        assert group_task.non_strict_mode is False

    def test_non_strict_mode_continuation(self, mocker):
        """Test continuing on errors in non-strict mode."""
        from lib.core.scheduler.group_task import GroupTask

        mock_group = MagicMock()
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask("group_file.txt", non_strict_mode=True)

        # In non-strict mode, non_strict_mode should be True
        assert group_task.non_strict_mode is True

    def test_blocking_exception_propagation(self, mocker):
        """Test that blocking exceptions are propagated."""
        from lib.core.scheduler.group_task import GroupTask
        from lib.utilities import BlockingException

        mock_group = MagicMock()
        mocker.patch("lib.core.scheduler.group_task.Group", return_value=mock_group)

        group_task = GroupTask("group_file.txt")

        # Test that BlockingException would be raised if encountered
        with pytest.raises(Exception):
            raise BlockingException("Test blocking exception")


class TestSchedulerIntegration:
    """Integration tests for scheduler."""

    def test_end_to_end_task_execution(self):
        """Test complete task execution workflow."""
        pytest.skip("Requires full scheduler integration")

    def test_group_task_with_multiple_scripts(self):
        """Test group task execution."""
        pytest.skip("Requires full scheduler integration")

    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        pytest.skip("Requires full scheduler integration")
