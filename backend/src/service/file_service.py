from typing import List
from fastapi import UploadFile

class file_Service:
    def __init__(self):
        pass
    
    def upload_file(self, files: List[UploadFile]):
        pass
    
    def delete_file_untranslated(self, file_names: List[str]):
        pass
    
    def delete_file_translated(self, file_names: List[str]):
        pass
