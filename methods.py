import os
from datetime import datetime

import db_models
from settings import *


# вывод файла по id
def get_file_from_db(db, file_id):
    return db.query(db_models.Image).filter(db_models.Image.file_id == file_id).first()

# offset\limit
def get_files_from_db_limit_offset(db, query, limit : int = None, offset : int = None):
    if limit and not offset:
        query = query[:limit]
    elif limit and offset:
        limit += offset
        query = query[offset:limit]
    elif not limit and offset:
        query = query[offset:]
    return query

# удаление файла из папки uploaded_files
def delete_file_from_uploads(file_name):
    try:
        os.remove(UPLOADED_FILES_PATH + file_name)
    except Exception as e:
        print(e)

# сохранение файла в папке uploaded_files
async def save_file_to_uploads(file, filename):
    with open(f'{UPLOADED_FILES_PATH}{filename}', "wb") as uploaded_file:
        file_content = await file.read()
        uploaded_file.write(file_content)
        uploaded_file.close()

# вывод полного имени
def format_filename(file, file_id=None, name=None):

    filename, ext = os.path.splitext(file.filename)

    # если имя не введено, то называем по id
    if name is None:
        filename = str(file_id)
    else:
        filename = name

    return filename + ext

# вывод размера
def get_file_size(filename, path : str = None):
    file_path = f'{UPLOADED_FILES_PATH}{filename}'
    if path:
        file_path = f'{path}{filename}'
    return os.path.getsize(file_path)

# добавление файла в бд
def add_file_to_db(db, **kwargs):
    new_file = db_models.Image(
                                file_id=kwargs['file_id'],
                                name=kwargs['full_name'],
                                tag=kwargs['tag'],
                                size=kwargs['file_size'],
                                mime_type=kwargs['file'].content_type,
                                modification_time=datetime.now()
                            )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file

# обновление файла в бд
def update_file_in_db(db, **kwargs):
    update_file = db.query(db_models.Image).filter(db_models.Image.file_id == kwargs['file_id']).first()
    update_file.name = kwargs['full_name']
    update_file.tag = kwargs['tag']
    update_file.size = kwargs['file_size']
    update_file.mime_type = kwargs['file'].content_type
    update_file.modification_time = datetime.now()

    db.commit()
    db.refresh(update_file)
    return update_file

# удаление файла из бд
def delete_file_from_db(db, file_info_from_db):
    db.delete(file_info_from_db)
    db.commit()
