# AUTO-GENERATED. DO NOT EDIT.

from typing import ClassVar, Mapping
from .configuration_abstract import ConfigurationAbstract


class Configuration(ConfigurationAbstract):
    __slots__ = ()

    INSTALL_MODE: ClassVar[str]
    MODULES_DIR: ClassVar[str]
    PLUGINS_DIR: ClassVar[str]
    BASH_SOURCE: ClassVar[str]
    APP_NAME: ClassVar[str]
    INSTALL_DIR: ClassVar[str]
    APP_DIR: ClassVar[str]
    USER_SYSTEM: ClassVar[str]
    USER_GROUP: ClassVar[str]
    USER_SYSTEM_HOME: ClassVar[str]
    APP_CONFIG_DIR: ClassVar[str]
    APP_DATA_DIR: ClassVar[str]
    INSTALLED_MODULES_DIR: ClassVar[str]
    APP_RUNTIME_DIR: ClassVar[str]
    APP_ENV_FILE: ClassVar[str]
    APP_ENV_PATH: ClassVar[str]
    MODULES_MANIFEST_FILE: ClassVar[str]
    MODULES_MANIFEST_PATH: ClassVar[str]
    AGENTS_DATA_RUNTIME: ClassVar[str]
    AGENTS_DATA_RUNTIME_PATH: ClassVar[str]
    AGENTS_DATA_COMMUNICATION_APP: ClassVar[str]
    APP_RUNTIME: ClassVar[str]
    APP_RUNTIME_PATH: ClassVar[str]
    AGENT_HOME_ROOT: ClassVar[str]
    AGENT_HOME_TEMPLATE: ClassVar[str]
    AGENT_CONFIG_DIR_NAME: ClassVar[str]
    AGENT_CONFIG_DIR_TEMPLATE: ClassVar[str]
    AGENT_CONFIG_FILE: ClassVar[str]
    AGENT_CONFIG_PATH_TEMPLATE: ClassVar[str]
    AGENT_RUNTIME_CONFIG_FILE: ClassVar[str]
    AGENT_RUNTIME_CONFIG_PATH_TEMPLATE: ClassVar[str]
    AGENT_SHELL_CONFIG_FILE: ClassVar[str]
    AGENT_SHELL_CONFIG_PATH_TEMPLATE: ClassVar[str]
    AGENT_SHELLS_DIR: ClassVar[str]
    AGENT_SHELLS_DIR_TEMPLATE: ClassVar[str]
    AGENT_AGENTRC_FILE: ClassVar[str]
    AGENT_AGENTRC_PATH_TEMPLATE: ClassVar[str]
    AGENT_BASHRC_FILE: ClassVar[str]
    AGENT_BASHRC_PATH_TEMPLATE: ClassVar[str]
    AGENT_HISTORY_DIR_NAME: ClassVar[str]
    AGENT_HISTORY_DIR_TEMPLATE: ClassVar[str]
    AGENT_HISTORY_FILE: ClassVar[str]
    AGENT_HISTORY_PATH_TEMPLATE: ClassVar[str]
    AGENT_INBOX_DIR_NAME: ClassVar[str]
    AGENT_INBOX_DIR_TEMPLATE: ClassVar[str]
    AGENT_COMMUNICATION_FILE: ClassVar[str]
    AGENT_COMMUNICATION_PATH_TEMPLATE: ClassVar[str]
    SYSTEM_AGENT_RUNTIME_SOCKET: ClassVar[str]
    SYSTEM_AGENT_RUNTIME_PID: ClassVar[str]
    COMMUNICATION_AGENT_RUNTIME_SOCKET: ClassVar[str]
    COMMUNICATION_AGENT_RUNTIME_PID: ClassVar[str]
    MAX_MESSAGE_BYTES_BASE: ClassVar[str]
    MAX_MESSAGE_BYTES_MULTIPLIER: ClassVar[str]

    @classmethod
    def schema(cls) -> Mapping[str, type]:
        return {
            'INSTALL_MODE': str,
            'MODULES_DIR': str,
            'PLUGINS_DIR': str,
            'BASH_SOURCE': str,
            'APP_NAME': str,
            'INSTALL_DIR': str,
            'APP_DIR': str,
            'USER_SYSTEM': str,
            'USER_GROUP': str,
            'USER_SYSTEM_HOME': str,
            'APP_CONFIG_DIR': str,
            'APP_DATA_DIR': str,
            'INSTALLED_MODULES_DIR': str,
            'APP_RUNTIME_DIR': str,
            'APP_ENV_FILE': str,
            'APP_ENV_PATH': str,
            'MODULES_MANIFEST_FILE': str,
            'MODULES_MANIFEST_PATH': str,
            'AGENTS_DATA_RUNTIME': str,
            'AGENTS_DATA_RUNTIME_PATH': str,
            'AGENTS_DATA_COMMUNICATION_APP': str,
            'APP_RUNTIME': str,
            'APP_RUNTIME_PATH': str,
            'AGENT_HOME_ROOT': str,
            'AGENT_HOME_TEMPLATE': str,
            'AGENT_CONFIG_DIR_NAME': str,
            'AGENT_CONFIG_DIR_TEMPLATE': str,
            'AGENT_CONFIG_FILE': str,
            'AGENT_CONFIG_PATH_TEMPLATE': str,
            'AGENT_RUNTIME_CONFIG_FILE': str,
            'AGENT_RUNTIME_CONFIG_PATH_TEMPLATE': str,
            'AGENT_SHELL_CONFIG_FILE': str,
            'AGENT_SHELL_CONFIG_PATH_TEMPLATE': str,
            'AGENT_SHELLS_DIR': str,
            'AGENT_SHELLS_DIR_TEMPLATE': str,
            'AGENT_AGENTRC_FILE': str,
            'AGENT_AGENTRC_PATH_TEMPLATE': str,
            'AGENT_BASHRC_FILE': str,
            'AGENT_BASHRC_PATH_TEMPLATE': str,
            'AGENT_HISTORY_DIR_NAME': str,
            'AGENT_HISTORY_DIR_TEMPLATE': str,
            'AGENT_HISTORY_FILE': str,
            'AGENT_HISTORY_PATH_TEMPLATE': str,
            'AGENT_INBOX_DIR_NAME': str,
            'AGENT_INBOX_DIR_TEMPLATE': str,
            'AGENT_COMMUNICATION_FILE': str,
            'AGENT_COMMUNICATION_PATH_TEMPLATE': str,
            'SYSTEM_AGENT_RUNTIME_SOCKET': str,
            'SYSTEM_AGENT_RUNTIME_PID': str,
            'COMMUNICATION_AGENT_RUNTIME_SOCKET': str,
            'COMMUNICATION_AGENT_RUNTIME_PID': str,
            'MAX_MESSAGE_BYTES_BASE': str,
            'MAX_MESSAGE_BYTES_MULTIPLIER': str,
        }
