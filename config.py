import configparser
from pathlib import Path


class Config:
    def __init__(self, parser: configparser.ConfigParser):
        self._parser = parser
        self.database_file = parser.get("Database", "File", fallback="/home/htp/cameratrap.db")

        self.sd_download_directory = Path(parser.get("SDCard", "DownloadFolder", fallback="/home/htp/camdata"))
        self.sd_download_directory.mkdir(exist_ok=True)

        self.sd_max_per_day = parser.getint("SDCard", "MaxPerDay", fallback=25)

        self.inference_command = parser.get("Inference", "Command", fallback=None)

        self.tensorflow_lite_model = parser.get("TensorFlowLite", "Model")
        self.tensorflow_lite_labels = parser.get("TensorFlowLite", "Labels")

        self.classify_max_attempts = parser.getint("Classify", "MaxAttempts", fallback=2)

        self.serial_port = parser.get("RockBLOCK", "SerialPort")
        self.rockblock_verbose = parser.getboolean("RockBLOCK", "Verbose", fallback=False)
        self.rockblock_verbose_serial = parser.getboolean("RockBLOCK", "VerboseSerial", fallback=False)
        self.rockblock_retry_attempts = parser.getint("RockBLOCK", "RetryAttempts", fallback=15)

        if len(parser["Mapping"]) == 0:
            raise Exception("Mappings must be specified in the config file")

        self.mapping = {}
        for key in parser["Mapping"]:
            value = parser.getint("Mapping", key)

            if value < 1 or value > 255:
                raise Exception(f"Mapping {key} with value {value} is not allowed, must be between 1 and 255")

            for k, v in self.mapping.items():
                if value == v:
                    raise Exception(f"Duplicate value ({v}) found for keys {k} and {key}")

            self.mapping[key] = value
