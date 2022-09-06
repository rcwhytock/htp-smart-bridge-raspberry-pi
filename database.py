import textwrap
from datetime import datetime as dt
from enum import Enum
from pathlib import Path
from typing import List

from peewee import *

from api import ApiFile
from inferencer import ClassificationResult


class EnumField(IntegerField):
    def __init__(self, choices, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
        self.choices = choices

    def db_value(self, value):
        return value.value

    def python_value(self, value):
        return self.choices(value)


class Photo(Model):
    class Status(Enum):
        TODO = 0
        INFERENCE_SUCCESS = 1
        INFERENCE_ERROR = 2
        SYNCED = 3

    id: int = AutoField()
    fingerprint: str = CharField(index=True, null=False)
    filename: str = CharField(null=False)
    directory: str = CharField(index=True, null=False)
    size: int = IntegerField(null=False)
    date: str = CharField(index=True, null=False)
    datetime: dt = DateTimeField(null=False)
    local_file: str = CharField(null=False)
    status: Status = EnumField(choices=Status, index=True, null=False, default=Status.TODO)
    inference_class: str = CharField(null=True)
    inference_attempt: int = IntegerField(null=True)
    inference_accuracy: float = FloatField(null=True)
    inference_error: str = CharField(null=True)
    inference_time: int = IntegerField(null=True)
    exif_datetime: dt = DateTimeField(null=True)


class Repository:
    def __init__(self, db: SqliteDatabase = SqliteDatabase('cameratrap.db')):
        self._db = db
        self._db.bind([Photo])
        self._db.create_tables([Photo])

    def get_fingerprint(self, file: ApiFile):
        return f"{file.directory.strip('/')}/{file.filename}/{file.datetime.isoformat()}/{file.size}"

    def format_day(self, datetime: dt):
        return datetime.strftime("%Y-%m-%d")

    def insert_photo(self, remote_file: ApiFile, output_file: Path):
        photo = Photo()
        photo.fingerprint = self.get_fingerprint(remote_file)
        photo.filename = remote_file.filename
        photo.directory = remote_file.directory
        photo.size = remote_file.size
        photo.datetime = remote_file.datetime
        photo.date = self.format_day(remote_file.datetime)
        photo.local_file = str(output_file.resolve())
        photo.save(force_insert=True)

    def get_photo_by_day_count(self, datetime: dt) -> int:
        return Photo.select(fn.Count()).where(Photo.date == self.format_day(datetime)).scalar()

    def get_photo_exists(self, remote_file: ApiFile) -> bool:
        return Photo.select().where(Photo.fingerprint == self.get_fingerprint(remote_file)).exists()

    def get_photos_to_inference(self) -> List[Photo]:
        return Photo.select().where(Photo.status == Photo.Status.TODO).order_by(Photo.datetime)

    def get_photos_to_sync(self) -> List[Photo]:
        return Photo.select().where(Photo.status == Photo.Status.INFERENCE_SUCCESS).order_by(Photo.datetime).limit(50)

    def update_photo_inference_success(self, photo_id: int, result: ClassificationResult, attempt: int) -> int:
        return Photo.update(
            status=Photo.Status.INFERENCE_SUCCESS,
            inference_time=result.time,
            inference_class=result.name,
            inference_accuracy=result.accuracy,
            exif_datetime=result.exif_datetime,
            inference_attempt=attempt,
        ).where(Photo.id == photo_id).execute()

    def update_photo_inference_error(self, photo_id: int, exception: Exception, attempt: int,
                                     status: Photo.Status) -> int:
        return Photo.update(
            status=status,
            inference_attempt=attempt,
            inference_error=textwrap.shorten(str(exception), 2000),
        ).where(Photo.id == photo_id).execute()

    def delete_photo(self, photo_id: int):
        Photo.delete().where(Photo.id == photo_id).execute()

    def update_photo_synced(self, photo_id: int):
        return Photo.update(
            status=Photo.Status.SYNCED,
        ).where(Photo.id == photo_id).execute()
