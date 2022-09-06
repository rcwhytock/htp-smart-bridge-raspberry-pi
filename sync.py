from typing import List, Dict

from api import Api, ApiFile
from config import Config
from database import Repository
from ping import Ping


class FileSyncManager:
    def __init__(self, config: Config, repository: Repository, api: Api, ping: Ping):
        self._config = config
        self._repository = repository
        self._api = api
        self._ping = ping

    def run(self):
        images = self._api.get_files()
        self.download_files(images)

    def download_files(self, files: List[ApiFile]):
        skipped = {}
        failure_count = 0
        for file in files:
            try:
                if self.should_download_file(file, skipped):
                    self.download_file(file)
            except Exception as e:
                failure_count += 1
                print(f"Error downloading file {file.directory}/{file.filename} {e}")
                if failure_count >= 3 and not self.is_host_reachable():
                    print(f"Abort downloading")
                    break

        if skipped:
            print(f"Skipped downloads because max ({self._config.sd_max_per_day}) per day is reached:")
            for key, value in skipped.items():
                print(f" - {key}: {value} download(s) skipped")

        return failure_count, skipped

    def is_host_reachable(self) -> bool:
        return self._ping.is_reachable(self._api.get_host(), attempts=1)

    def should_download_file(self, file: ApiFile, skipped: Dict[str, int] = None) -> bool:
        if self._repository.get_photo_exists(file):
            return False

        if self._config.sd_max_per_day > 0:
            if self._repository.get_photo_by_day_count(file.datetime) >= self._config.sd_max_per_day:
                if skipped is not None:
                    key = file.datetime.strftime('%d-%m-%Y')
                    skipped[key] = (skipped[key] if key in skipped else 0) + 1
                return False

        return True

    def download_file(self, file: ApiFile):
        local_dir = self._config.sd_download_directory / file.directory.strip("/")
        local_dir.mkdir(parents=True, exist_ok=True)
        output_file = local_dir / file.filename

        if output_file.is_file() and output_file.stat().st_size == file.size:
            print(f"File already exists {output_file}...")
        else:
            print(f"Downloading file {file.directory}/{file.filename} to {output_file}...")
            self._api.download_file(file, str(output_file))

        self._repository.insert_photo(file, output_file)
