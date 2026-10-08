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
    INSTALLING_INSTALLED = 'installing_installed'
    # Installationstatuses only for debug
    INSTALLING_INSTALLATION_ERROR = 'installing_installation_error'
    INSTALLING_LOAD_AGENT_DATA = 'installing_load_agent_data'

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

    # Removing statuses
    REMOVING_REMOVED = "rremoving_removed"
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
    