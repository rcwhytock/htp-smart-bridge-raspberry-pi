#!/usr/bin/env python3
import argparse
from array import array
import configparser
from pathlib import Path
from peewee import SqliteDatabase
from api import EzShareApi
from classify import FileClassifier
from communication import Communicator
from communicator_rockblock import SatelliteCommunicator
from config import Config
from read_pmp import read_pmp
from database import Repository
from encoder import KEEP_ALIVE, SatelliteEncoder
from ping import Ping
from sync import FileSyncManager
import subprocess
from tensorflow_inferencer import TensorFlowLiteInferencer
from uploader import Uploader


class SmartCameraTrap:
    def __init__(self, config: Config, reachable: bool):
        self._config = config
        self._ping = Ping()
        self._version = self.read_version()
        self._pmp_data = read_pmp()
        self._activation = str(self._pmp_data.get("activation", "unknown")).lower()
        self._sdcard_reachable = reachable

    def read_version(self) -> int:
        try:
            with open("version.txt", mode='r') as f:
                return int(f.read())
        except Exception as e:
            print("Could get version", e)
            return 0

    def logrotate(self):
        try:
            subprocess.check_call(["logrotate", "/etc/logrotate.conf"])
        except Exception as e:
            print("Error running logrotate", e)

    def run(self):
        repository = Repository(SqliteDatabase(self._config.database_file))

        if self._sdcard_reachable:
            FileSyncManager(self._config, repository, EzShareApi(), self._ping).run()

        inferencer = TensorFlowLiteInferencer(self._config)
        FileClassifier(repository, inferencer, self._config.classify_max_attempts).run()

        communicators: array[Communicator] = [
            SatelliteCommunicator(self._config),
        ]

        encoder = SatelliteEncoder(self._config.mapping, self._pmp_data, self._version)

        Uploader(communicators, repository, encoder, self._activation == KEEP_ALIVE).run()

        self.logrotate()
        print("Done")


if __name__ == '__main__':
    def file_path(path):
        p = Path(path)
        if p.is_file():
            return p
        else:
            raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


    def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')


    parser = argparse.ArgumentParser(description='Smart Camera Trap Processing')
    parser.add_argument('--config', help='configuration file', type=file_path, default="config.ini")
    parser.add_argument('--reachable', help='if wifi SD card was reachable', type=str2bool, default="True")

    args = parser.parse_args()

    parser = configparser.ConfigParser()
    parser.read(args.config)
    SmartCameraTrap(Config(parser), args.reachable).run()
