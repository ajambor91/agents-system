import json


class JsonLoader:

  
    @staticmethod
    def getJsonFileContent(file_path):
        file_data = None
        with open(file_path, "r") as f:
            file_data = json.load(f)
        if file_data is None:
            raise RuntimeError("Failed to load data from file")
        
        return file_data