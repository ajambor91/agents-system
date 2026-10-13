from enum import Enum

class AgentStatus(Enum):

    # Installation statuses important for cleaning
    INSTALLING_UNINITIALIZED = 'installing_uninitialized'
    INSTALLING_INITIALIZED = 'installing_initialized'
    INSTALLING_VALIDATED = 'installing_validated'
    INSTALLING_ASSIGNED = 'installing_assigned'
    INSTALLING_CREATED_SOURCE_PATH = 'installing_created_source_path'
    INSTALLING_CREATED_TEMP_DIR = 'installing_created_temp_dir'
    INSTALLING_CREATED_TARGET_DIR = 'installing_created_target_dir'
    INSTALLING_COPIED_TEMP = 'installing_copied_temp'
    INSTALLING_USER_CREATED = 'installing_user_created'
    INSTALLING_SET_PRIV = 'installing_set_privileges'
    INSTALLING_AGENBT_RUNTIME_INSTALLED = 'installing_agent_runtime_installed'
    INSTALLING_COPIED_DATA_FILES = 'installing_copied_data_files'
    INSTALLING_REMOVED_TEMP = 'installing_removed_temp'
    INSTALLING_ENTRY_ADDED = 'installing_entry_added'
    INSTALLING_LINKED_AGENT_PERSONALITY_FILES = 'installing_link_agent_personality_files'
    INSTALLING_APPLIED_PERSONALITY = 'installing_applied_personality'
    INSTALLING_LINKED_AGENT_SCRIPTS_FILES = 'installing_link_agent_scripts_files'
    INSTALLING_INSTALLED = 'installing_installed'
    # Installationstatuses only for debug
    INSTALLING_INSTALLATION_ERROR = 'installing_installation_error'
    INSTALLING_LOAD_AGENT_DATA = 'installing_load_agent_data'
    INSTALLING_CHECKING_AGENT_EXISTS = 'installing_checking_agent_exists'
    #Cleaning statuses
    CLEANING_CLEANED = 'cleaning_cleaned'
    CLEANING_ERROR = 'cleaning_error'
    CLEANING_INITIALIZED = 'cleaning_initialized'
    CLEANING_CLEANED_ENTRY = 'cleaning_cleaned_entry'
    CLEANING_CLEANED_AGENT = 'cleaning_cleaned_agent'
    CLEANING_CLEANED_USER = 'cleaning_cleaned_user'
    CLEANING_CLEANED_TEMP = 'cleaning_cleaned_temp'
    CLEANING_CLEANED_SOURCE = 'cleaning_cleaned_source'
    CLEANING_CLEANED_TARGET = 'cleaning_cleaned_target'
    CLEANING_NO_NEEDED = 'cleaning_no_needed'
    # Removing statuses
    REMOVING_REMOVED = "removing_removed"
    REMVIGN_REMOVED_ERROR = 'removing_removed_error'
    REMOVING_INITIALIZED = 'removing_initiallized'
    REMOVING_CREATED = 'removing_created'
    REMOVING_REMOVE_USER = 'removing_remove_user'
    REMOVING_REMOVE_AGENT = 'removing_remove_agent'
    REMOVING_REMOVE_TARGET = 'removing_remove_target'
    REMOVING_REMOVE_TEMP = 'removing_remove_temp'
    REMOVING_REMOVE_ENTRY = 'removing_remove_entry'
    REMOVING_GET_AGENT_PATH = 'removing_get_agent_path'
    REMOVING_GET_AGENT_DATA = 'removing_get_agent_data'

    RUNNING_RUN_INITIALIED = 'running_run_initialized'
    RUNNING_GET_AGENT_PATH = 'running_get_agent_path'
    RUNNING_GET_AGENT_DATA = 'running_get_agent_data'
    RUNNING_AGENT_CREATED = 'running_agent_created'

    RUNNING_SUCCESS = 'running_success'
    RUNNING_FAILED = 'running_failed'
    