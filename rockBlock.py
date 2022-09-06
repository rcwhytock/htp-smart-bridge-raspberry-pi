from re import match, Pattern, compile
from time import sleep
import serial
import datetime
from random import randint


class RockBlockException(Exception):
    pass


class SBDStatus:
    def __init__(self, mo_status_code, mo_message_number, mt_status_code, mt_message_number, mt_length, mt_queued):
        self.mo_status_code = mo_status_code
        self.mo_message_number = mo_message_number
        self.mt_status_code = mt_status_code
        self.mt_message_number = mt_message_number
        self.mt_length = mt_length
        self.mt_queued = mt_queued
        self.mo_success = 0 <= mo_status_code <= 4
        self.mt_success = 0 <= mt_status_code <= 1

    def mo_status_message(self):
        if self.mo_status_code == 0:
            return "MO message, if any, transferred successfully."
        elif self.mo_status_code == 1:
            return "MO message, if any, transferred successfully, but the MT message in the queue was too big to be transferred."
        elif self.mo_status_code == 2:
            return "MO message, if any, transferred successfully, but the requested Location Update was not accepted."
        elif 3 <= self.mo_status_code <= 8:
            return "Reserved, but indicate MO session success if used."
        elif self.mo_status_code == 10:
            return "Gateway reported that the call did not complete in the allowed time."
        elif self.mo_status_code == 11:
            return "MO message queue at the Gateway is full."
        elif self.mo_status_code == 12:
            return "MO message has too many segments."
        elif self.mo_status_code == 13:
            return "Gateway reported that the session did not complete."
        elif self.mo_status_code == 14:
            return "Invalid segment size."
        elif self.mo_status_code == 15:
            return "Access is denied."
        elif self.mo_status_code == 16:
            return "Transceiver has been locked and may not make SBD calls (see +CULK command)."
        elif self.mo_status_code == 17:
            return "Gateway not responding (local session timeout)."
        elif self.mo_status_code == 18:
            return "Connection lost (RF drop)."
        elif 19 <= self.mo_status_code <= 31:
            return "Reserved, but indicate MO session failure if used."
        elif self.mo_status_code == 32:
            return "No network service, unable to initiate call."
        elif self.mo_status_code == 33:
            return "Antenna fault, unable to initiate call."
        elif self.mo_status_code == 34:
            return "Radio is disabled, unable to initiate call (see *Rn command)."
        elif self.mo_status_code == 35:
            return "Transceiver is busy, unable to initiate call (typically performing auto-registration)."
        elif self.mo_status_code == 36:
            return "Reserved, but indicate failure if used."
        else:
            return f"Unknown code {self.mo_status_code}."


def _assert_match(pattern: Pattern, value):
    # Check to see if line matches pattern
    result = match(pattern, value)

    if result is not None:
        return result
    else:
        raise RockBlockException(f"Expected to match pattern {pattern} but got {value}")


class RockBlock(object):
    IRIDIUM_EPOCH = 1399818235000  # May 11, 2014, at 14:23:55 (This will be 're-epoched' every couple of years!)
    _signal_strength_response_pattern = compile(r'\+CSQ:(\d)')
    _network_time_response_pattern = compile(r'-MSSTM: (.*)')
    # +SBDIX: <MO status>, <MOMSN>, <MT status>, <MTMSN>, <MT length>, <MT queued>
    _session_response_pattern = compile(r'\+SBDIX: (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)')

    # by default use a random delay:
    # - between 0..5 for the first 3 attempts
    # - between 5..20 for the next 3 attempts
    # - between 20..40 for the subsequent attempts
    session_retry_delays = [range(2, 5)] * 3 + [range(5, 15)] * 7 + [range(15, 20)]

    def __init__(self, port_id: str, debug: bool=False, debug_serial: bool=False, session_retry_attempts: int=15):
        self._debug = debug
        self._debug_serial = debug_serial
        self._session_retry_attempts = session_retry_attempts
        self.s = serial.Serial(port_id, 19200, timeout=5)
        if not self._configure_port():
            self.close()
            raise RockBlockException("Could not communicate with RockBLOCK")

        self.s.timeout = 60

    def _read_line(self):
        data = self.s.readline().decode().strip()
        if self._debug_serial:
            print(f"<- {data}")

        return data

    def _assert_blank_ok(self):
        self._assert_read_line("")
        self._assert_read_line("OK")

    def _assert_read_line(self, assertion):
        actual = self._read_line()
        if actual != assertion:
            raise RockBlockException(f"Expected to read '{assertion}' but got '{actual}'")
        return actual

    def _write_command(self, command: str):
        self._write(f"{command}\r")

        # Assert echo response
        self._assert_read_line(command)

    def _write(self, data: str):
        if self._debug_serial:
            print(f"-> {data}")
        return self.s.write(data.encode())

    def _write_bytes(self, data: bytes):
        if self._debug_serial:
            print(f"-> {data}")
        return self.s.write(data)

    def _write_command_and_read_line(self, command):
        self._write_command(command)
        return self._read_line()

    def ping(self):
        return self._write_command_and_read_line("AT") == "OK"

    def request_signal_strength(self):
        self._ensure_connection_status()
        result = _assert_match(
            self._signal_strength_response_pattern,
            self._write_command_and_read_line("AT+CSQ")
        )
        self._assert_blank_ok()
        return int(result.group(1))

    def network_time(self):
        self._ensure_connection_status()
        result = _assert_match(
            self._network_time_response_pattern,
            self._write_command_and_read_line("AT-MSSTM")
        )

        self._assert_blank_ok()

        if result.group(1) == "no network service":
            return None
        else:
            return datetime.datetime.utcfromtimestamp(int((self.IRIDIUM_EPOCH + (int(result.group(1), 16) * 90)) / 1000))

    def send(self, msg: str):
        return self.send_bytes(msg.encode("ascii"))

    def send_bytes(self, msg: bytes):
        self._queue_bytes_message(msg)
        return self._try_extended_sbd_session()

    def check_mailbox(self):
        return self._try_extended_sbd_session()

    def get_serial_identifier(self):
        self._ensure_connection_status()
        response = self._write_command_and_read_line("AT+GSN")
        self._assert_blank_ok()
        return response

    def close(self):
        if self.s is not None:
            self.s.close()
            self.s = None

    def receive_ascii_message(self):
        self._write_command("AT+SBDRT")
        self._assert_read_line("+SBDRT:")
        response = self._read_line()
        self._assert_read_line("OK")
        return response

    def _queue_bytes_message(self, msg: bytes):
        self._clear_mo_buffer()
        self._ensure_connection_status()

        if len(msg) > 340:
            raise RockBlockException(f"_queue_bytes_message bytes should be <= 340 bytes, was {len(msg)} bytes")

        self._write_command("AT+SBDWB=" + str(len(msg)))
        self._assert_read_line("READY")

        checksum = 0

        for c in msg:
            checksum = checksum + c

        self._write_bytes(msg + bytes([checksum >> 8]) + bytes([checksum & 0xFF]))
        self._assert_read_line("")  # BLANK

        status = self._read_line()

        if status == "0":
            self._assert_read_line("")  # BLANK
            self._assert_read_line("OK")  # OK
        elif status == "1":
            raise RockBlockException("SBD message write timeout. An insufficient number of bytes were transferred to "
                                     "ISU during the transfer period of 60 seconds.")
        elif status == "2":
            raise RockBlockException("SBD message checksum sent from DTE does not match the checksum calculated at "
                                     "the ISU.")
        elif status == "3":
            raise RockBlockException("SBD message size is not correct. The maximum mobile originated SBD message "
                                     "length is 340 bytes. The minimum mobile originated SBD message length is 1 "
                                     "byte.")
        else:
            raise RockBlockException(f"Unknown status writing binary message {status}")

    def _configure_port(self):
        return self._enable_echo() and self._disable_flow_control() and self._disable_ring_alerts() and self.ping()

    def _enable_echo(self):
        return self._write_command_and_read_line("ATE1") == "OK"

    def _disable_flow_control(self):
        return self._write_command_and_read_line("AT&K0") == "OK"

    def _disable_ring_alerts(self):
        return self._write_command_and_read_line("AT+SBDMTA=0") == "OK"

    def _get_session_retry_delay(self, i: int) -> int:
        r = self.session_retry_delays[i] if i < len(self.session_retry_delays) else self.session_retry_delays[-1]
        return randint(r.start, r.stop)

    def _try_extended_sbd_session(self) -> SBDStatus:
        for n in range(self._session_retry_attempts):
            if self._debug:
                print(f"Trying to create extended SBD session, attempt {n + 1}/{self._session_retry_attempts}")

            status = self._extended_sbd_session()
            if status.mo_success:
                return status
            else:
                # When we have run out of attempts, return the faulty session status
                if n == self._session_retry_attempts - 1:
                    return status

                delay = self._get_session_retry_delay(n)

                if self._debug:
                    print(f"No success trying to create extended SBD session, retry in {delay} second(s): {status.mo_status_message()}")
                sleep(delay)

    def _extended_sbd_session(self) -> SBDStatus:
        self._ensure_connection_status()

        result = _assert_match(
            self._session_response_pattern,
            self._write_command_and_read_line("AT+SBDIX")
        )

        self._assert_blank_ok()

        status = SBDStatus(
            int(result.group(1)),
            int(result.group(2)),
            int(result.group(3)),
            int(result.group(4)),
            int(result.group(5)),
            int(result.group(6))
        )

        if status.mo_success:
            self._clear_mo_buffer()

        return status

    def _clear_mo_buffer(self):
        if self._write_command_and_read_line("AT+SBDD0") == "0":
            self._assert_read_line("")
            self._assert_read_line("OK")

    def _ensure_connection_status(self):
        if self.s is None or self.s.isOpen() is False:
            raise RockBlockException("Serial port not connected")


if __name__ == '__main__':

    def list_ports():
        import sys
        import glob
        ports = []
        if sys.platform.startswith('win'):
            ports = ['COM' + str(i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')

        result = []

        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass

        return result


    print(list_ports())
    rb = RockBlock("/dev/ttyUSB0", debug=True, debug_serial=True)
    time = rb.network_time()
    print(time)
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    # print(rb.send_bytes(bytearray.fromhex("02540b1d11ff40f7251411ff32f8251411ff3af8251411ff4cf8251411ff50f82514")))
    # for _ in range(200):
    #     print(rb.request_signal_strength())
    #     sleep(1)
