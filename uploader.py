from typing import List
from communication import Communicator
from database import Repository
from encoder import SatelliteEncoder


class Uploader:
    def __init__(self, communicators: List[Communicator], repository: Repository, encoder: SatelliteEncoder, force_upload: bool):
        self._communicators = communicators
        self._force_upload = force_upload
        self._repository = repository
        self._encoder = encoder

    def run(self):
        # For now just send one batch at a time
        return self._send_batch()

    # Returns True when all the data has been sent, False when images still need to be synced
    def _send_batch(self) -> bool:
        images = self._repository.get_photos_to_sync()
        payload, encoded_images = self._encoder.encode_images(images)

        if len(encoded_images) == 0 and not self._force_upload:
            return True

        try:
            print("Sending payload...", payload.hex())
            for communicator in self._communicators:
                if communicator.is_available():
                    if communicator.send_data(payload):
                        print("Sending payload succeeded")
                        for image in encoded_images:
                            self._repository.update_photo_synced(image.id)
                        break
                    else:
                        print("Sending payload failed")
        except Exception as e:
            print(f"Error sending data {e}")

        return len(images) == len(encoded_images)
