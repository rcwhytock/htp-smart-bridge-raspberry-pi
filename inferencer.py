from pathlib import Path
import datetime


class ClassificationResult:
    def __init__(self, _name: str, _accuracy: float, _time: int, _exif_datetime: datetime.datetime = None):
        self.name = _name
        self.accuracy = _accuracy
        self.time = _time
        self.exif_datetime = _exif_datetime

    def __str__(self):
        return f"{self.name} {self.accuracy} {self.time}ms {self.exif_datetime}"


class Inferencer:
    def infer(self, local_file: Path) -> ClassificationResult:
        pass
