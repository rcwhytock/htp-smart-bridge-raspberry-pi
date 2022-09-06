import datetime
import re
import urllib.parse
from typing import Optional, List
from xml.etree import ElementTree
import requests


class ApiFile:
    filename: str
    directory: str
    size: int
    datetime: datetime.datetime

    def __str__(self):
        return f"{self.directory}/{self.filename} - {self.datetime}"


class HttpClient:
    def __init__(self, host: str, request_timeout=20):
        self._host_name = host
        self._base_url = f"http://{host}"
        self._request_timeout = request_timeout

    def build_url(self, path: str, params: dict = None):
        url = f"{self._base_url}/{path}"
        if params is not None:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        return url

    def http_get(self, path: str, params: dict = None):
        return requests.get(self.build_url(path, params), timeout=self._request_timeout)

    def stream_url_to_file(self, url: str, to_file: str):
        with requests.get(url, stream=True, timeout=self._request_timeout) as r:
            r.raise_for_status()
            with open(to_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

    def get_host(self) -> str:
        return self._host_name

    def get_files(self) -> List[ApiFile]:
        pass

    def download_file(self, file: ApiFile, to_file: str):
        pass


class Api:
    def __init__(self, client: HttpClient):
        self.client = client

    def get_host(self) -> str:
        return self.client.get_host()

    def get_files(self) -> List[ApiFile]:
        pass

    def download_file(self, file: ApiFile, to_file: str):
        pass


class EzShareApi(Api):
    __max_dirs = 2
    __max_files = 100

    def __init__(self, client=HttpClient("192.168.4.1")):
        super().__init__(client)

    def get_files(self) -> List[ApiFile]:
        files = []
        directories = self.get_directories_to_process()
        for directory in directories:
            files.extend(self.list_files(directory))
        return files

    def get_directories_to_process(self) -> List[str]:
        print(f"Fetching directories to process...")
        res = self.client.http_get("client", {"command": "GetFolders"})
        directories = []

        root = ElementTree.fromstring(res.content.decode('gb2312'))
        count = 0
        for child in root.findall("folders/folder[@type='1']"):
            if count >= self.__max_dirs:
                break
            directories.append(child.find("name").text)
            count = count + 1

        return directories

    def list_files(self, directory: str) -> List[ApiFile]:
        res = self.client.http_get("client",
                                   {"command": "GetFiles", "pageNum": self.__max_files, "folderDir": directory})
        files = []

        root = ElementTree.fromstring(res.content.decode('gb2312'))
        for child in root.findall("photos/photo[@type='0']"):
            files.append(self.__parse_file(child, directory))

        return files

    def download_file(self, file: ApiFile, to_file: str):
        url = self.client.build_url("download", {"fname": file.filename, "fdir": file.directory})
        self.client.stream_url_to_file(url, to_file)

    def __parse_file(self, child: ElementTree.Element, directory: str) -> Optional[ApiFile]:
        filename = child.find("name").text
        if not filename.lower().endswith(".jpg"):
            return
        photo = ApiFile()
        photo.directory = directory
        photo.filename = filename
        photo.size = int(child.find("fileSize").text)
        photo.datetime = self.__parse_date_time(int(child.find("createTime").text))
        return photo

    def __parse_date_time(self, creat_time: int) -> datetime.datetime:
        fcrdate = ((creat_time >> 16) & 65535)
        fcrtime = (65535 & creat_time)

        year = ((fcrdate & 65024) >> 9) + 1980
        month = (fcrdate & 480) >> 5
        day = fcrdate & 31
        hour = (fcrtime & 63488) >> 11
        minute = (fcrtime & 2016) >> 5
        second = (fcrtime & 31) * 2
        return datetime.datetime(year, month, day, hour, minute, second)
