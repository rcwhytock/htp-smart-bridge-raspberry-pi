from pathlib import Path
from database import Photo, Repository
from inferencer import Inferencer


class FileClassifier:
    def __init__(self, repository: Repository, inferencer: Inferencer, max_attempts: int = 2):
        self._repository = repository
        self._inferencer = inferencer
        self._max_attempts = max_attempts

    def run(self):
        self.__classify_images()

    def __classify_images(self):
        photos = self._repository.get_photos_to_inference()
        print(f"Classifying {len(photos)} image(s)...")
        for photo in photos:
            local_file = Path(photo.local_file)
            try:
                if local_file.is_file():
                    res = self._inferencer.infer(local_file)
                    print(f"Classification result: {res.name} with accuracy {res.accuracy} in {res.time}ms {local_file}")
                    self._repository.update_photo_inference_success(photo.id, res, (photo.inference_attempt or 0) + 1)
                    local_file.unlink()
                else:
                    print(f"Cannot classify, file is missing: {local_file}")
                    self._repository.delete_photo(photo.id)
            except Exception as e:
                print(f"Error classifying file {local_file} {e}")
                attempt = (photo.inference_attempt or 0) + 1
                status = Photo.Status.INFERENCE_ERROR if attempt >= self._max_attempts else Photo.Status.TODO
                if local_file.is_file() and status == Photo.Status.INFERENCE_ERROR:
                    local_file.unlink()

                self._repository.update_photo_inference_error(photo.id, e, attempt, status)
