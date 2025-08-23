from digit_interface.digit import Digit
from digit_interface.digit_handler import DigitHandler


class DigitController:
    """
    A controller class for managing the DIGIT device connection and operations.

    Author: Gemma McLean
    Date: June 2025
    """

    def __init__(self):
        """
        Initialise the DigitController to manage DIGIT connections and streams.
        Auto connects to the first available DIGIT device.
        """

        # Connect and store the instance and serial number
        self.digit, self.serial = self._connect_to_digit()

        # Lists of available stream data
        self.stream_strings = []  # Combobox text e.g. 'VGA 30fps'
        self.mode_options = []  # VGA or QVGA
        self.fps_options = []  # Frames per second int values e.g. 15, 30, 60
        self.resolutions = []  # Resolution dicts e.g. {'width': 640, 'height': 480}
        self._populate_stream_lists()

    # --- Private helpers ---
    def _check_for_digits(self):
        """
        Check for connected DIGIT devices.

        Returns:
            list: A list of dictionaries containing DIGIT device information.
            None: If no DIGIT devices are found.
        """

        digits = DigitHandler.list_digits()
        if digits:
            return digits
        return None

    def _connect_to_digit(self):
        """
        Connect to the first available DIGIT device.

        Returns:
            tuple: A tuple containing the DIGIT instance and its serial number.
            (None, None): If no DIGIT devices are found or connection fails.
        """

        digits = self._check_for_digits()
        if digits:
            try:
                # Get the first digit's serial number
                serial = digits[0]['serial']
                # Create a Digit instance with the serial number
                digit = Digit(serial, 'Single_Digit')
                # Connect to the DIGIT device
                digit.connect()
                print(f'Connected to DIGIT with serial number: {serial}')
                # Return the connected Digit instance and its serial number
                return digit, serial
            except Exception as e:
                print(f'Failed to connect to DIGIT: {e}')
                return None, None
        else:
            print('No DIGIT devices found.')
            return None, None

    def _populate_stream_lists(self):
        """
        Populate the stream strings, mode options, fps options, and resolutions lists
        based on the STREAMS dictionary
        """

        if self.digit:
            # Get the STREAMS dictionary
            stream_dict = self.digit.STREAMS
            # Iterate through the STREAMS dictionary to populate the lists
            for mode, mode_info in stream_dict.items():
                for _, fps_value in mode_info['fps'].items():
                    stream_string = f'{mode} {fps_value}fps'
                    self.stream_strings.append(stream_string)
                    self.mode_options.append(mode)
                    self.fps_options.append(fps_value)
                    self.resolutions.append(mode_info['resolution'])

    # --- Public getters ---
    def get_stream_strings(self):
        """
        Get the list of stream strings for the combobox.

        Returns:
            list: A list of stream strings formatted as 'VGA 30fps', 'QVGA 60fps', etc.
        """

        return self.stream_strings

    def get_max_intensity(self):
        """
        Get the maximum intensity value.

        Returns:
            int: The maximum intensity value if available, None otherwise.
        """

        if self.digit:
            return self.digit.LIGHTING_MAX
        return None

    def get_min_intensity(self):
        """
        Get the minimum intensity value.

        Returns:
            int: The minimum intensity value if available, None otherwise.
        """

        if self.digit:
            return self.digit.LIGHTING_MIN
        return None

    def get_stream_mode(self):
        """
        Get the current stream mode e.g. 'VGA' or 'QVGA'.

        Returns:
            str: The current stream mode if available, None otherwise.
        """

        if self.digit:
            # Get resolution
            res = self.digit.resolution
            # Get index of resolution in resolutions list
            if res in self.resolutions:
                index = self.resolutions.index(res)
                # Return the corresponding stream mode
                return self.mode_options[index]
        return None

    def get_resolution(self):
        """
        Get the current resolution e.g. {'width': 640, 'height': 480}.

        Returns:
            dict: The current resolution if available, None otherwise.
        """

        if self.digit:
            return self.digit.resolution
        return None

    def get_fps(self):
        """
        Get the current frames per second (fps) e.g. 15, 30 or 60.

        Returns:
            int: The current fps if available, None otherwise.
        """

        if self.digit:
            return self.digit.fps
        return None

    def get_intensity(self):
        """
        Get the current intensity.

        Returns:
            int: The current intensity value if available, None otherwise.
        """

        if self.digit:
            return self.digit.intensity
        return None

    def get_frame(self):
        """
        Get the current video frame from the DIGIT device.

        Returns:
            np.ndarray: The current video frame if available, None otherwise.
        """

        if self.digit:
            return self.digit.get_frame()
        return None

    # --- Public setters/actions ---
    def set_stream(self, index):
        """
        Set the stream mode, fps, and resolution based on the index of the chosen
        stream string from the combobox.

        Args:
            index (int): The index of the selected stream string in the combobox.

        Returns:
            bool: True if the stream was set successfully, False otherwise.
        """

        if self.digit:
            try:
                stream_mode = self.mode_options[index]
                fps = self.fps_options[index]
                fps_text = f'{fps}fps'
                fps_setting = Digit.STREAMS[stream_mode]['fps'][fps_text]
                self.digit.set_fps(fps_setting)
                res = self.resolutions[index]
                self.digit.set_resolution({'resolution': res})
                return True
            except Exception as e:
                print(f'Failed to set stream: {e}')
                return False
        return False

    def set_intensity(self, value):
        """
        Set the intensity (value should be between min and max intensity).

        Args:
            value (int): The intensity value to set.

        Returns:
            bool: True if the intensity was set successfully, False otherwise.
        """

        if self.digit:
            try:
                # Ensure value is within bounds
                if self.get_min_intensity() <= value <= self.get_max_intensity():
                    self.digit.set_intensity(value)
                    return True
                else:
                    print(f'Intensity value {value} out of bounds.')
                    return False
            except Exception as e:
                print(f'Failed to set intensity: {e}')
                return False
        return False

    def disconnect(self):
        """Disconnect the DIGIT device."""

        if self.digit:
            try:
                self.digit.disconnect()
            except Exception as e:
                print(f'Failed to disconnect DIGIT: {e}')

    # --- Status/check methods ---
    def is_connected(self):
        """
        Check if the DIGIT device is connected.

        Returns:
            bool: True if connected, False otherwise.
        """

        if DigitHandler.find_digit(self.serial):
            return True
        return False
