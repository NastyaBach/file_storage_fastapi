from settings import *
from methods import *

from fastapi import FastAPI, Response, status, Depends, Query, File, UploadFile
from typing import Optional, List
from starlette.responses import FileResponse

import db_models
from db_connect import engine, SessionLocal
from sqlalchemy.orm import Session


### База данных
db_models.Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
### Конец базы данных


app = FastAPI()


# Вывод файлов
@app.get("/api/get", tags=["Get files"], status_code=status.HTTP_200_OK)
async def root(
                response: Response,
                id: Optional[List[int]] = Query(None),
                name: Optional[List[str]] = Query(None),
                tag: Optional[List[str]] = Query(None),
                limit: Optional[int] = None,
                offset: Optional[int] = None,
                db: Session = Depends(get_db)
            ):

    # Все записи по умолчанию
    query = db.query(db_models.Image).all()
    files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели только id
    if id and not name and not tag:
        query = db.query(db_models.Image).filter(db_models.Image.file_id.in_(id)).all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели id и имя
    elif id and name and not tag:
        query = db.query(db_models.Image).filter(db_models.Image.file_id.in_(id)) \
                                        .filter(db_models.Image.name.in_(name)) \
                                        .all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели все три параметра
    elif id and name and tag:
        query = db.query(db_models.Image).filter(db_models.Image.file_id.in_(id)) \
                                        .filter(db_models.Image.name.in_(name)) \
                                        .filter(db_models.Image.tag.in_(tag)) \
                                        .all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели id и тэг
    elif id and not name and tag:
        query = db.query(db_models.Image).filter(db_models.Image.file_id.in_(id)) \
                                        .filter(db_models.Image.tag.in_(tag)) \
                                        .all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели имя и тэг
    elif not id and name and tag:
        query = db.query(db_models.Image).filter(db_models.Image.name.in_(name)) \
                                        .filter(db_models.Image.tag.in_(tag)) \
                                        .all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели только тэг
    elif not id and not name and tag:
        query = db.query(db_models.Image).filter(db_models.Image.tag.in_(tag)).all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если ввели только имя
    elif not id and name and not tag:
        query = db.query(db_models.Image).filter(db_models.Image.name.in_(name)).all()
        files_in_db = get_files_from_db_limit_offset(db, query, limit, offset)

    # Если с фильтрами не нашлось ни одного файла, то ошибка
    if len(files_in_db) == 0:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'message': 'No results =('}

    response.status_code = status.HTTP_200_OK
    return files_in_db


# загрузка и обновление файлов
@app.post("/api/upload", tags=["Upload"], status_code=status.HTTP_200_OK)
async def upload_file(
                        response: Response,
                        file_id: int,
                        name: Optional[str] = None,
                        tag: Optional[str] = None,
                        file: UploadFile = File(...),
                        db: Session = Depends(get_db)
                    ):

    # данные нового файла: файл, id, имя
    full_name = format_filename(file, file_id, name)

    # сохранение файла
    await save_file_to_uploads(file, full_name)

    # размер файла
    file_size = get_file_size(full_name)

    # достаём информацию из бд
    file_info_from_db = get_file_from_db(db, file_id)

    # если файл ещё не был загружен
    if not file_info_from_db:
        response.status_code = status.HTTP_201_CREATED
        return add_file_to_db(
                                db,
                                file_id=file_id,
                                full_name=full_name,
                                tag=tag,
                                file_size=file_size,
                                file=file
                            )

    # если файл есть и его нужно обновить
    if file_info_from_db:
        # удаляем файл из uploaded_files
        delete_file_from_uploads(file_info_from_db.name)

        response.status_code = status.HTTP_201_CREATED
        return update_file_in_db(
                                    db,
                                    file_id=file_id,
                                    full_name=full_name,
                                    tag=tag,
                                    file_size=file_size,
                                    file=file
                                )


# скачивание файла
@app.get("/api/download", tags=["Download"], status_code=status.HTTP_200_OK)
async def download_file(
                        response: Response,
                        file_id: int,
                        db: Session = Depends(get_db)
                    ):
    file_info_from_db = get_file_from_db(db, file_id)

    if file_info_from_db:
        file_resp = FileResponse(UPLOADED_FILES_PATH + file_info_from_db.name,
                                media_type=file_info_from_db.mime_type,
                                filename=file_info_from_db.name)
        response.status_code = status.HTTP_200_OK
        return file_resp
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'msg': 'File not found'}


# Удаление файла
@app.delete("/api/delete", tags=["Delete"])
async def delete_file(
                        response: Response,
                        file_id: int,
                        db: Session = Depends(get_db)
                    ):
    file_info_from_db = get_file_from_db(db, file_id)

    # если файл найден
    if file_info_from_db:
        # удаление из бд
        delete_file_from_db(db, file_info_from_db)

        # удаление из папки
        delete_file_from_uploads(file_info_from_db.name)

        response.status_code = status.HTTP_200_OK
        return {'msg': f'File {file_info_from_db.name} successfully deleted'}
    # Если файла нет в бд - ошибка
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'msg': f'File does not exist'}
