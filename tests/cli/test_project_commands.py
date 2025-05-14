# """Tests for project CLI commands."""
# 
# import json
# import os
# from pathlib import Path
# from tempfile import TemporaryDirectory
# 
# import pytest
# from typer.testing import CliRunner
# 
# from basic_memory.cli.main import app
# from basic_memory.config import ConfigManager, DATA_DIR_NAME, CONFIG_FILE_NAME
# 
# 
# @pytest.fixture
# def temp_home(monkeypatch):
#     """Create a temporary directory for testing."""
#     # Save the original environment variable if it exists
#     original_env = os.environ.get("BASIC_MEMORY_PROJECT")
# 
#     # Clear environment variable for clean test
#     if "BASIC_MEMORY_PROJECT" in os.environ:
#         del os.environ["BASIC_MEMORY_PROJECT"]
# 
#     with TemporaryDirectory() as tempdir:
#         temp_home = Path(tempdir)
#         monkeypatch.setattr(Path, "home", lambda: temp_home)
# 
#         # Ensure config directory exists
#         config_dir = temp_home / DATA_DIR_NAME
#         config_dir.mkdir(parents=True, exist_ok=True)
# 
#         yield temp_home
# 
#         # Cleanup: restore original environment variable if it existed
#         if original_env is not None:
#             os.environ["BASIC_MEMORY_PROJECT"] = original_env
#         elif "BASIC_MEMORY_PROJECT" in os.environ:
#             del os.environ["BASIC_MEMORY_PROJECT"]
# 
# 
# @pytest.fixture
# def cli_runner():
#     """Create a CLI runner for testing."""
#     return CliRunner()
# 
# 
# def test_project_list_empty(cli_runner, temp_home):
#     """Test listing projects when none are configured."""
#     # Create empty config but with main project (will always be present)
#     config_file = temp_home / DATA_DIR_NAME / CONFIG_FILE_NAME
#     config_file.write_text(json.dumps({"projects": {}, "default_project": "main"}))
# 
#     # Run command
#     result = cli_runner.invoke(app, ["project", "list"])
#     assert result.exit_code == 0
#     # The test will always have at least the "main" project due to auto-initialization
#     assert "main" in result.stdout
# 
# 
# def test_project_list(cli_runner, temp_home):
#     """Test listing projects."""
#     # Create config with projects
#     config_file = temp_home / DATA_DIR_NAME / CONFIG_FILE_NAME
#     config_data = {
#         "projects": {
#             "main": str(temp_home / "basic-memory"),
#             "work": str(temp_home / "work-memory"),
#         },
#         "default_project": "main",
#     }
#     config_file.write_text(json.dumps(config_data))
# 
#     # Run command
#     result = cli_runner.invoke(app, ["project", "list"])
#     assert result.exit_code == 0
#     assert "main" in result.stdout
#     assert "work" in result.stdout
#     assert "basic-memory" in result.stdout
#     assert "work-memory" in result.stdout
# 
# 
# def test_project_add(cli_runner, temp_home):
#     """Test adding a project."""
#     # Create config manager to initialize config
#     config_manager = ConfigManager()
# 
#     # Create a project directory
#     test_project_dir = temp_home / "test-project"
# 
#     # Run command
#     result = cli_runner.invoke(app, ["project", "add", "test", str(test_project_dir)])
#     assert result.exit_code == 0
#     assert "Project 'test' added at" in result.stdout
# 
#     # Verify project was added
#     config_manager = ConfigManager()
#     assert "test" in config_manager.projects
#     assert Path(config_manager.projects["test"]) == test_project_dir
# 
# 
# def test_project_add_existing(cli_runner, temp_home):
#     """Test adding a project that already exists."""
#     # Create config manager and add a project
#     config_manager = ConfigManager()
#     config_manager.add_project("test", str(temp_home / "test-project"))
# 
#     # Try to add the same project again
#     result = cli_runner.invoke(app, ["project", "add", "test", str(temp_home / "another-path")])
#     assert result.exit_code == 1
#     assert "Error: Project 'test' already exists" in result.stdout
# 
# 
# def test_project_remove(cli_runner, temp_home):
#     """Test removing a project."""
#     # Create config manager and add a project
#     config_manager = ConfigManager()
#     config_manager.add_project("test", str(temp_home / "test-project"))
# 
#     # Remove the project
#     result = cli_runner.invoke(app, ["project", "remove", "test"])
#     assert result.exit_code == 0
#     assert "Project 'test' removed" in result.stdout
# 
#     # Verify project was removed
#     config_manager = ConfigManager()
#     assert "test" not in config_manager.projects
# 
# 
# def test_project_default(cli_runner, temp_home):
#     """Test setting the default project."""
#     # Create config manager and add a project
#     config_manager = ConfigManager()
#     config_manager.add_project("test", str(temp_home / "test-project"))
# 
#     # Set as default
#     result = cli_runner.invoke(app, ["project", "default", "test"])
#     assert result.exit_code == 0
#     assert "Project 'test' set as default and activated" in result.stdout
# 
#     # Verify default was set
#     config_manager = ConfigManager()
#     assert config_manager.default_project == "test"
# 
#     # Extra verification: check if the environment variable was set
#     assert os.environ.get("BASIC_MEMORY_PROJECT") == "test"
# 
# 
# def test_project_current(cli_runner, temp_home):
#     """Test showing the current project."""
#     # Create a bare-bones config.json with main as the default project
#     config_file = temp_home / DATA_DIR_NAME / CONFIG_FILE_NAME
#     config_data = {
#         "projects": {
#             "main": str(temp_home / "basic-memory"),
#         },
#         "default_project": "main",
#     }
#     config_file.write_text(json.dumps(config_data))
# 
#     # Create the main project directory
#     main_dir = temp_home / "basic-memory"
#     main_dir.mkdir(parents=True, exist_ok=True)
# 
#     # Now check the current project
#     result = cli_runner.invoke(app, ["project", "current"])
#     assert result.exit_code == 0
#     assert "Current project: main" in result.stdout
#     assert "Path:" in result.stdout
#     assert "Database:" in result.stdout
# 
# 
# def test_project_option(cli_runner, temp_home, monkeypatch):
#     """Test using the --project option."""
#     # Create config manager and add a project
#     config_manager = ConfigManager()
#     config_manager.add_project("test", str(temp_home / "test-project"))
# 
#     # Mock environment to capture the set variable
#     env_vars = {}
#     monkeypatch.setattr(os, "environ", env_vars)
# 
#     # Run command with --project option
#     cli_runner.invoke(app, ["--project", "test", "project", "current"])
# 
#     # Verify environment variable was set
#     assert env_vars.get("BASIC_MEMORY_PROJECT") == "test"
# 
# 
# def test_project_default_activates_project(cli_runner, temp_home, monkeypatch):
#     """Test that setting the default project also activates it in the current session."""
#     # Create a test environment
#     env = {}
#     monkeypatch.setattr(os, "environ", env)
# 
#     # Create two test projects
#     config_manager = ConfigManager()
#     config_manager.add_project("project1", str(temp_home / "project1"))
# 
#     # Set project1 as default using the CLI command
#     result = cli_runner.invoke(app, ["project", "default", "project1"])
#     assert result.exit_code == 0
#     assert "Project 'project1' set as default and activated" in result.stdout
# 
#     # Verify the environment variable was set
#     # This is the core of our fix - the set_default_project command now also sets
#     # the BASIC_MEMORY_PROJECT environment variable to activate the project
#     assert env.get("BASIC_MEMORY_PROJECT") == "project1"
