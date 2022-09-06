import subprocess
from time import sleep


class Ping:
    def __init__(self, verbose: bool = False):
        self._verbose = verbose

    def is_reachable(self, host: str, attempts: int = 10, delay: int = 1, verbose: bool = False):
        print(f"Testing if {host} is reachable...")
        for _ in range(attempts):
            if subprocess.call(['ping', '-c', '1', host], stdout=None if verbose else subprocess.DEVNULL) == 0:
                print(f"Host {host} reached.")
                return True
            sleep(delay)

        print(f"Host {host} not reachable.")
        return False


if __name__ == '__main__':
    ping = Ping(False)
    ping.is_reachable("google.com")
