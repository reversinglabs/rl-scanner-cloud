import os

UPLOAD_FILE_SIZE_LIMIT = 10737418240  # 10GB


class FileValidator:
    @staticmethod
    def validate_file(file_path: str) -> None:
        if not os.path.exists(file_path):
            raise RuntimeError("File does not exist")

        if os.path.getsize(file_path) > UPLOAD_FILE_SIZE_LIMIT:
            raise RuntimeError("File size is larger than 10GB")
