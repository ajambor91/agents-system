
from __future__ import annotations
import re
from pathlib import Path


SAFE_NAME = re.compile(r"^[a-z_][a-z0-9_-]*$")
SAFE_APP_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
REQUIRED_DEFAULTS: set[str] = set()
MARKER_NAME = ".agents-system-install.json"
UNIT_ROOT = Path("/etc/systemd/system")


ENVIRONMENT_FILE = "app_env.json"
ENVIRONMENT_KIND = "agents-system-environment"
INSTALLATION_KIND = "agents-system-installation"
JOURNAL_KIND = "agents-system-install-journal"
INSTALLATION_SUCCESS_STATUSES = frozenset({"success"})
LIFECYCLE_IDENTITY_VARIABLES = (
    "INSTALL_MODE", "APP_NAME", "INSTALL_DIR", "APP_DIR", "MODULES_DIR",
    "USER_SYSTEM", "USER_GROUP", "USER_SYSTEM_HOME", "APP_CONFIG_DIR",
    "APP_DATA_DIR", "APP_RUNTIME_DIR", "INSTALLED_MODULES_DIR", "APP_ENV_FILE",
    "APP_ENV_PATH", "MODULES_MANIFEST_FILE", "MODULES_MANIFEST_PATH",
)
CONFIGURATION_PATH_FIELDS = (
    "package_dir", "user_home", "install_dir", "config_dir", "data_dir",
    "runtime_dir", "commands_dir",
)
CONFIGURATION_BOOLEAN_FIELDS = ("force", "dedicated_user", "clone_repo", "verbose")
SOURCE_ENV_RELATIVE_PATH = Path("src/.env")
GENERATED_CONFIGURATION_RELATIVE_PATH = Path("src/lib/configuration/configuration.py")
GENERATED_ARTIFACT_RELATIVE_PATHS = (
    SOURCE_ENV_RELATIVE_PATH,
    GENERATED_CONFIGURATION_RELATIVE_PATH,
    Path("resources/app_env.json"), Path("resources/agents-system.module.json"),
    Path("src/resources/app_env.json"), Path("src/resources/agents-system.module.json"),
)
DEV_RUNTIME_SOCKET_VARIABLES = ("SYSTEM_AGENT_RUNTIME_SOCKET", "COMMUNICATION_AGENT_RUNTIME_SOCKET")

INSTALLER_MODULE_NAME = "install"
INSTALLER_SOURCE_RELATIVE_PATH = Path("install/src")
INSTALLER_MODULE_RELATIVE_PATH = Path("src/install")
HELP_MANIFEST_FILES = {
    "install": "installer.json", "uninstall": "uninstaller.json",
    "reinstall": "reinstaller.json", "reconfigure": "reconfigure.json",
    "rollback": "rollback.json",
}
LIFECYCLE_HOST_COMMANDS = {
    "asystem-uninstall": "uninstall", "asystem-reinstall": "reinstall",
    "asystem-reconfigure": "reconfigure",
}

APPLICATION_DIRECTORY_MODE = 0o2770
APPLICATION_FILE_MODE = 0o660
APPLICATION_EXECUTABLE_MODE = 0o770
