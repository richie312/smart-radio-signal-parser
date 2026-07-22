import socket

class RadioController:
    """
    Handles core tuning and verification via the SDR++ Rigctl server.
    """
    def __init__(self, ip="127.0.0.1", port=4532):
        self.ip = ip
        self.port = port

    def tune_frequency(self, frequency_hz):
        """
        Sends a standard command string to change the SDR++ active VFO frequency.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((self.ip, self.port))
                command = f"F {int(frequency_hz)}\n"
                s.sendall(command.encode('utf-8'))
                response = s.recv(1024).decode('utf-8').strip()
                return response == "RPRT 0"
        except Exception:
            return False

    def verify_active_frequency(self):
        """
        Queries the current active frequency directly from the SDR++ tuner.
        Returns: int (Frequency in Hz) or -1 if connection fails.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect((self.ip, self.port))
                
                # 'f' queries the active frequency in rigctl protocol
                s.sendall(b"f\n")
                response = s.recv(1024).decode('utf-8').strip()
                
                # SDR++ returns the frequency as a raw number string (e.g. '91100000')
                if response.isdigit():
                    return int(response)
                return -1
        except Exception:
            return -1
