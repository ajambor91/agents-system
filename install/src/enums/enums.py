from enum import Enum


class InstallerMode(str, Enum):
    INSTALL = "install"
    ROLLBACK = "rollback"
    UNINSTALL = "uninstall"
    REINSTALL = "reinstall"
    RECONFIGURE = "reconfigure"
