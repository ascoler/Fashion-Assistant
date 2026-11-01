from pathlib import Path
from pymongo import MongoClient
import os
import uuid
import datetime
class DB:
    def __init__(self):
        self.client = MongoClient("localhost", 27017)
        self.db = self.client["rec_db"]
        self.collection = self.db["rec"]

class WorkWithDB(DB):
    def set_photo(self, file_name: str, path: str,user_id:str,tags:list[str],description:str):
        
        
        self.file_name = file_name
        self.path = path
        
        self.user_id = user_id
        self.tags = tags
        
        
        self.description = description
        
        self.create_data = datetime.datetime.now()
        
        self.size = os.path.getsize(self.path)
            
        self.image_info = {
            "file_name": self.file_name,
            "path": self.path,
            "size": self.size,
            
            
            "user_id": self.user_id,
            "tags":self.tags,
            
            
            "data":self.create_data,
            "description":self.description
        }
    
    def insert_in_db(self):
        
        
        self.collection.insert_one(self.image_info)
        return f"Файл {self.file_name} успешно добавлен в базу!"
    def get_photos(self, limit: int = 10) -> list:
        
        return list(self.collection.find().limit(limit))