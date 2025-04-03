import json

class FileReader():
    def __init__(self):
        pass

    def read(self, file_path: str) -> str:
        with open(file_path, 'r') as file:
            return file.read()

    def read_lines(self, file_path: str) -> list[str]:
        with open(file_path, 'r') as file:
            return file.readlines()

    def read_bytes(self, file_path: str) -> bytes:
        with open(file_path, 'rb') as file:
            return file.read()

    def read_json(self, file_path: str) -> dict:
        with open(file_path, 'r') as file:
            return json.load(file)
