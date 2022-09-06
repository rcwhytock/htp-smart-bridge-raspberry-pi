from communication import Communicator
from rockBlock import RockBlock
from config import Config
from gpiozero import LED
from time import sleep
import warnings

warnings.simplefilter('ignore')

class SatelliteCommunicator(Communicator):
    def __init__(self, config: Config):
        self._config = config

    def is_available(self) -> bool:
        return self._config.serial_port is not None

    def send_data(self, payload: bytearray) -> bool:
        rockblock_pin2 = LED(26)
        rockblock_pin2.on()

        sleep(10)
        try:
            for _ in range(5):
                try:
                    return self.__do_send_data(payload)
                except Exception as e:
                    sleep(5)
                    print(f"Error communicating with RockBLOCK {e}")
        finally:
            rockblock_pin2.off()
            
        return False

    def __do_send_data(self, payload: bytearray) -> bool:
        rb = None

        try:
            rb = RockBlock(self._config.serial_port,
                           debug=self._config.rockblock_verbose,
                           debug_serial=self._config.rockblock_verbose_serial,
                           session_retry_attempts=self._config.rockblock_retry_attempts)

            status = rb.send_bytes(bytes(payload))
            time = rb.network_time()
            formatted_time = "Unknown"

            if time is not None:
                formatted_time = time.strftime("%Y-%m-%dT%H:%M:%SZ")

            print(f"Sending via RockBlock finished - "
                  f"success: {status.mo_success}, "
                  f"message_number: {status.mo_message_number}, "
                  f"time: {formatted_time}, "
                  f"status: {status.mo_status_message()}")
            return status.mo_success
        finally:
            if rb is not None:
                rb.close()
