from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config
from inferencer import Inferencer, ClassificationResult
import time
import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite


class TensorFlowLiteInferencer(Inferencer):
    def __init__(self, config: Config):
        self._interpreter = tflite.Interpreter(config.tensorflow_lite_model)
        self._interpreter.allocate_tensors()
        _, height, width, _ = self._interpreter.get_input_details()[0]['shape']
        self._input_tensor_size = (width, height)
        self._labels = self._load_labels(config.tensorflow_lite_labels)

    def _load_labels(self, path):
        with open(path, 'r') as f:
            return {i: line.strip() for i, line in enumerate(f.readlines())}

    def _set_input_tensor(self, image):
        tensor_index = self._interpreter.get_input_details()[0]['index']
        input_tensor = self._interpreter.tensor(tensor_index)()[0]
        input_tensor[:, :] = image

    def _open_image(self, fn) -> Image:
        x = Image.open(fn)
        x.draft('RGB', self._input_tensor_size)
        return x.resize(self._input_tensor_size, Image.ANTIALIAS)

    def _classify_image(self, image, top_k=1):
        """Returns a sorted array of classification results."""
        self._set_input_tensor(image)
        self._interpreter.invoke()
        output_details = self._interpreter.get_output_details()[0]
        output = np.squeeze(self._interpreter.get_tensor(output_details['index']))

        # If the model is quantized (uint8 data), then dequantize the results
        if output_details['dtype'] == np.uint8:
            scale, zero_point = output_details['quantization']
            output = scale * (output - zero_point)

        ordered = np.argpartition(-output, top_k)
        return [(self._labels[i], output[i]) for i in ordered[:top_k]]

    def get_exif_datetime(self, image: Image) -> Optional[datetime]:
        try:
            return datetime.strptime(image.getexif()[36867], '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            print("Error getting exif date", e)
            return None

    def infer(self, local_file: Path) -> ClassificationResult:
        start = time.time() * 1000
        image = self._open_image(local_file)
        class_name, accuracy = self._classify_image(image)[0]
        duration = time.time() * 1000 - start
        return ClassificationResult(class_name, accuracy, int(duration), self.get_exif_datetime(image))


if __name__ == '__main__':
    path = Path("models")

    for modelfile in path.glob('*.tflite'):
        print()
        print(modelfile)
        print("---------------")
        class FakeConfig(object):
            def __init__(self):
                self.tensorflow_lite_model = str(modelfile)
                self.tensorflow_lite_labels = str(modelfile.parent/modelfile.stem) + ".txt"


        rb = TensorFlowLiteInferencer(FakeConfig())
        
        for file in path.glob('*.[Jj][Pp][Gg]'):
            print(file.name, rb.infer(file))
