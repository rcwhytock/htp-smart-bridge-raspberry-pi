#!/usr/bin/env python3
import argparse
import re
from time import sleep
import os
import subprocess
import warnings
from gpiozero import LED
import serial

warnings.simplefilter('ignore')


class SmartCameraTrapMain:
    __HOST = "192.168.4.1"
    __PMP_DATA_FILE = f"serial.log"
    __CORE_TIMEOUT = 20 * 60  # 20 minutes timeout

    __status_pin = LED(18)

    def run(self, skip_pmp: bool):
        self.set_status_pin(True)
        should_halt = not skip_pmp
        
        if not skip_pmp:
            if not self.detect_pmp():
                # If PMP not detected retry once more, otherwise RPi is booted without the PMP and then don't run the normal program.
                if not self.detect_pmp():
                    self.set_status_pin(False)
                    print("PMP not detected aborting image processing")
                    return

        try:
            reachable = self.is_reachable(self.__HOST)
            if reachable:
                self.upgrade_if_needed()
            self.run_core(reachable)
        except Exception as e:
            print("Main error", e)
        finally:
            self.set_status_pin(False)

        if should_halt:
            self.halt()

    def set_status_pin(self, on: bool):
        if on:
            print("Raising status pin")
            self.__status_pin.on()
        else:
            print("Lowering status pin")
            self.__status_pin.off()

    def halt(self):
        print("Shutting down the system")
        subprocess.check_call(["halt"])

    def run_core(self, reachable: bool):
        subprocess.check_call(["python3", "-u", "core.py", "--reachable", str(reachable)], timeout=self.__CORE_TIMEOUT)

    def detect_pmp(self) -> bool:
        print("Detecting PMP...")
        ser = None

        if os.path.exists(self.__PMP_DATA_FILE):
            os.remove(self.__PMP_DATA_FILE)

        try:
            ser = serial.Serial('/dev/ttyAMA0', baudrate=115200, stopbits=1, parity="N", timeout=10)
            with open(self.__PMP_DATA_FILE, 'w') as pmp_data_file:
                start_token_seen = False
                while True:
                    line = ser.readline().decode('ascii').strip()
                    if len(line) == 0:  # When we reach the first timeout
                        print("PMP not detected.")
                        break

                    if line == "START VALUES":
                        start_token_seen = True
                        continue

                    if start_token_seen and line == "END VALUES":
                        print("PMP detected")
                        return True

                    if start_token_seen:
                        print("-> ", line)
                        pmp_data_file.write(line)
                        pmp_data_file.write('\n')

        except Exception as e:
            print("Error detecting PMP", e)
        finally:
            if ser is not None:
                ser.close()

        return False

    def is_reachable(self, host: str, attempts: int = 30, delay: int = 1, verbose: bool = False):
        print(f"Testing if {host} is reachable...")
        for _ in range(attempts):
            try:
                if subprocess.call(['ping', '-c', '1', host], stdout=subprocess.STDOUT if verbose else subprocess.DEVNULL, stderr=subprocess.STDOUT if verbose else subprocess.DEVNULL, timeout=20) == 0:
                    print(f"Host {host} reached.")
                    return True
            except Exception as e:
                print("Error pinging", e)
            sleep(delay)

        print(f"Host {host} not reachable.")
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Smart Camera Trap Main')
    parser.add_argument('--skip-pmp', help='skip PMP detection', action="store_true")
    args = parser.parse_args()

    SmartCameraTrapMain().run(args.skip_pmp)
