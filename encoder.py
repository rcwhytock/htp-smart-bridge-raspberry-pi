from datetime import datetime
from typing import List, Tuple, Mapping

from database import Photo

KEEP_ALIVE = "alive"

# Encodes image classifications 
class SatelliteEncoder:
    SAT_EPOCH = datetime(2010, 1, 1, 0, 0, 0)
    MESSAGE_TYPE_IMAGE_CLASSIFICATION = (1).to_bytes(1, byteorder='little')
    MESSAGE_VERSION = (1).to_bytes(1, byteorder='little')
    BYTES_PER_IMAGE = 6

    def __init__(self, class_mapping: Mapping[str, int], pmp_data: dict, version: int):
        # Convert keys to lower case to make mapping case insensitive
        self._class_mapping = dict((k.lower(), v) for k, v in class_mapping.items())
    
        self._pmp_data = pmp_data
        self._version = version
        self._activation = str(self._pmp_data.get("activation", "unknown")).lower()

    def encode_images(self, images: List[Photo]) -> Tuple[bytearray, List[Photo]]:
        payload = bytearray()
        # TODO Encode information into byte array in a format you want to read it in the backend

        images_to_send = []

        for image in images:
            append = self.encode_image(image)

            if len(payload) + len(append) > 340:
                break
            else:
                payload.extend(append)
                images_to_send.append(image)

        return payload, images_to_send

    def encode_image(self, image: Photo) -> bytes:
        payload = bytearray()
        # TODO Encode image information into byte array in a format you want to read it in the backend
        return payload
