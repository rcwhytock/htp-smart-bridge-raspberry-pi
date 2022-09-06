class Communicator:
    def is_available(self) -> bool:
        """Check if this communicator is available"""
        pass

    def send_data(self, payload: bytearray) -> bool:
        """Send payload"""
        pass

