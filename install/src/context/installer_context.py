from ..enums import InstallerMode
INSTALLER_MODE: InstallerMode | None = None


def set_mode(installer_mode: str) -> None:
    global INSTALLER_MODE
    INSTALLER_MODE = InstallerMode(installer_mode)
def get_mode() -> InstallerMode:
    if INSTALLER_MODE is None:
        raise Exception("Installer mode cannot be None")
    return INSTALLER_MODE
