import zipfile
import os

def create_zip(files_dict, zip_name="papers.zip"):
    zip_path = os.path.join("outputs", zip_name)

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for format_name, file_types in files_dict.items():
            for file_type, file_path in file_types.items():
                if os.path.exists(file_path):
                    arcname = f"{format_name}.{file_type}"
                    zipf.write(file_path, arcname=arcname)

    return zip_path