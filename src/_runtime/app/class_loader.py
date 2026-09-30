from .models.module_entry import ModuleEntry
from .models.meta_data_class import MetaDataClass

from shared.json_loader import JsonLoader

class ClassLoader:
    _META_FILE_NAME = None
    _modules_list = None
    _foundClasses = None
    def __init__(self, modules_list):
        self._META_FILE_NAME = 'meta.json'
        self._modules_list = modules_list
        self._foundClasses = self._getModulesList()

    def loadClasses(self):
        self._foundClasses = self._getModulesListFile()
        return self

    def getClasses(self):
        return self._foundClasses

    def _getModulesList(self):
        
        if self.modules_list is None:
            raise RuntimeError("Configuration not set for ClassLoader")
        extracted_modules_list = dict[string, object] = {}
        modules_data = self._modules_list['children'];
        for module in modules_data:
            runtime = module['runtime']
            if runtime is None or runtime.size == 0:
                continue
            meta_content = JsonLoader.getJsonFileContent()
            module_class_name = meta_content['application']['class']
            module_name = meta_content['application']['module']
            module_namespace = meta_content['namespace']
            module_entrypoint =meta_content['entrypoint']
            
            module_name = module['module_name']
            is_runtime =  module['is_runtime']
            absolute_module_path = module['absolute_module_path']
            meta_class = MetaDataClass(module_namespace, module_entrypoint, module_name, module_class_name) 
            module_entry = ModuleEntry(absolute_module_path, is_runtime, runtime, module_name, meta_class) 
            extracted_modules_list[module_name] = module_entry
        return extracted_modules_list


            
