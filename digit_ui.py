import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
from digit_controller import DigitController
from digit_popup import DigitPopup
import json
import os

"""
Author: Gemma McLean
Date: May 2025
A class for creating a user interface for the DIGIT device using Tkinter.
"""

DEFAULT_PADDING = 10
USER_PREFS_FILE = "digit_ui_prefs.json"


class DigitUI:
    def __init__(self, root):
        """
        Initialise the Digit UI application.
        Args:
            root (tk.Tk): The root window for the application.
        """
        # Initialise DigitController and root window
        self.dc = None
        self.root = root

        # Track if the UI has been created
        self.ui = False
        # Track if the live video view is running
        self.view_running = False
        # Set the update interval for video frames
        self.update_interval = 33  # Default to ~30 FPS if not set

        # Set up the root window
        self.root.title("DIGIT UI")
        self.root.geometry("640x480")
        self.root.resizable(False, False)

        # Try and connect to DIGIT
        self.try_connect_digit()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def close_app(self):
        """Handle the application close event."""
        # If the UI has been created, save user preferences
        if self.ui:
            self.save_prefs()
        # If the DIGIT device is connected, disconnect it
        if self.dc.digit:
            self.dc.disconnect()
        # Stop the live view
        self.view_running = False
        # Destroy the root window
        self.root.destroy()

    def try_connect_digit(self):
        """Try to connect to the DIGIT device. If it fails, show a popup."""
        # Create a DigitController instance to find and connect to the DIGIT device
        self.dc = DigitController()
        # Check if the DIGIT device is connected
        if self.dc.digit is None:
            # If not connected, show a popup
            self.show_connection_failed_popup()
        else:
            # If connected, set up the UI
            self.setup_ui()

    def setup_ui(self):
        """Set up the main UI components after a successful connection to DIGIT."""
        # Create and place the main frames
        self.create_settings_frame().grid(row=0, column=0,
                                          padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
        self.create_live_view_frame().grid(row=0, column=1,
                                           padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
        # Mark the UI as created
        self.ui = True
        # Load and apply saved user preferences
        prefs = self.load_prefs()
        self.apply_prefs(prefs)

    def create_settings_frame(self):
        """
        Create the settings frame with RGB intensity and stream mode controls.
        Returns:
            tk.LabelFrame: The settings frame containing the controls.
        """
        # Create a LabelFrame for whole section
        settings_frame = tk.LabelFrame(
            self.root, text="Settings", borderwidth=2, relief="groove")

        # --- RGB intensity components ---
        # Create frame for intensity label and slider elements
        intensity_frame = tk.Frame(settings_frame)

        # Create the label
        intensity_label = tk.Label(intensity_frame, text="RGB Intensity:")

        # Get the min and max intensity values from the DigitController
        min_intensity = self.dc.get_min_intensity()
        max_intensity = self.dc.get_max_intensity()

        # Create the slider with the range of min to max intensity
        self.intensity_slider = tk.Scale(intensity_frame,
                                         from_=min_intensity,  # 0
                                         to=max_intensity,  # 15
                                         orient=tk.HORIZONTAL,
                                         command=self.on_intensity_slider_change)
        # For some reason when we get the intensity, it is in the range of 0-4095.
        # Yet when we set the intensity, it is in the range of 0-15.
        # We need to convert it to a range of 0-15 for the slider and the setter.
        # The conversion is done by dividing the intensity value by 263.
        intensity_val = self.dc.get_intensity()
        intensity_val = intensity_val // 263
        # Set initial slider value to current intensity
        self.intensity_slider.set(intensity_val)

        # Pack the components into the intensity frame
        intensity_label.pack()
        self.intensity_slider.pack()
        # ---------------------------------

        # --- Stream mode components ---
        # Create frame for stream label and slider elements
        stream_frame = tk.Frame(settings_frame)

        # Create the label
        stream_label = tk.Label(stream_frame, text="Stream Mode:")

        # Create the combobox with stream options from DigitController
        self.stream_combobox = ttk.Combobox(
            stream_frame,
            values=self.dc.get_stream_strings(),
            state="readonly",
        )

        # Set initial combobox value based on current stream mode and fps
        stream_mode = self.dc.get_stream_mode()
        fps = self.dc.get_fps()
        stream_text = f"{stream_mode} {fps}fps"
        self.stream_combobox.set(stream_text)

        # Bind the combobox selection change event
        self.stream_combobox.bind("<<ComboboxSelected>>", self.on_stream_combobox_change)

        # Pack the components into the stream frame
        stream_label.pack()
        self.stream_combobox.pack()
        # ---------------------------------

        # Pack the frames into the settings frame with padding
        intensity_frame.pack(pady=DEFAULT_PADDING, padx=DEFAULT_PADDING)
        stream_frame.pack(pady=DEFAULT_PADDING, padx=DEFAULT_PADDING)

        # Return the settings frame to be placed in the main UI
        return settings_frame

    def create_live_view_frame(self):
        """
        Create the live view frame to display the video feed from DIGIT.
        Returns:
            tk.LabelFrame: The live view frame containing the video feed.
        """
        # Create a LabelFrame for whole section
        live_view_frame = tk.LabelFrame(
            self.root, text="DIGIT Live View", borderwidth=2, relief="groove")

        # Create a label to display the video feed
        self.video_label = tk.Label(live_view_frame)

        # Pack the frame into the live_view frame with padding
        self.video_label.pack(padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)

        # Start the live video view
        self.view_running = True
        self.update_video_frame()

        # Return the live view frame to be placed in the main UI
        return live_view_frame

    def update_video_frame(self):
        """ Update the video frame in the live view."""
        # If the live view is running
        if self.view_running:
            try:
                # Get the current video frame from DIGIT
                frame = self.dc.get_frame()
                if frame is not None:
                    # Convert frame (BGR to RGB)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Resize to 320x240
                    frame_rgb = cv2.resize(frame_rgb, (240, 320))
                    # Convert to PIL Image then to PhotoImage
                    image = Image.fromarray(frame_rgb)
                    self.photo = ImageTk.PhotoImage(image=image)
                    # Update label image
                    self.video_label.config(image=self.photo)

                # Schedule next update based on current FPS
                self.root.after(self.update_interval, self.update_video_frame)
            except Exception as e:
                # If an error occurs, disable the UI and show a lost connection popup
                print(f"Error updating video frame: {e}")
                self.disable_ui()
                self.show_lost_connection_popup()

    def on_intensity_slider_change(self, value):
        """
        Handle the slider change event to set the RGB intensity.
        Args:
            value (str): The new value of the slider as a string.
        """
        # Convert the slider value to an integer and set the intensity
        self.dc.set_intensity(int(value))

    def on_stream_combobox_change(self, event):
        """
        Handle the combobox selection change event.
        Args:
            event (tk.Event): The event triggered by the combobox selection change.
        """
        # Set the stream based on the selected index in the combobox
        success = self.dc.set_stream(self.stream_combobox.current())
        if success:
            # Update the live view update interval based on new fps
            fps = self.dc.get_fps()
            self.update_interval = 1000 // fps
            # Refresh the capture FPS calculation based on new fps
            # TODO

    def show_connection_failed_popup(self):
        """Show a popup window if the connection fails with options to retry or exit."""
        # Create and display the failed connection popup
        failed_popup = DigitPopup(
            self.root,
            title="Connection Failed",
            message="Failed to connect to a DIGIT sensor.",
            buttons=[
                ("Retry", lambda: self.retry_connection(failed_popup)),
                ("Exit", self.close_app)
            ]
        )
        # Handle the popup close event
        failed_popup.protocol("WM_DELETE_WINDOW", self.close_app)

    def retry_connection(self, popup):
        """
        Retry the connection to DIGIT and close the popup.
        Args:
            popup (DigitPopup): The popup window to close.
        """
        # Close the popup window and try to connect again
        popup.destroy()
        self.try_connect_digit()

    def show_lost_connection_popup(self):
        """Show a popup window when the connection to DIGIT is lost."""
        # Create and display the lost connection popup
        lost_popup = DigitPopup(
            self.root,
            title="Lost Connection",
            message="Lost connection to DIGIT.\nPlease reconnect and relaunch.",
            buttons=[("OK", self.close_app)]
        )
        # Handle the popup close event
        lost_popup.protocol("WM_DELETE_WINDOW", self.close_app)

    def disable_ui(self):
        """Disable all UI elements in the root window to prevent further interaction."""
        # Disable all widgets in the root window
        for widget in self.root.winfo_children():
            try:
                widget.configure(state="disabled")
            except Exception:
                # Some widgets may not support the 'state' attribute
                pass

    def save_prefs(self):
        """Save user preferences to a JSON file."""
        prefs = {
            "intensity": self.dc.get_intensity(),
            "stream_index": self.stream_combobox.current(),
            # Add more preferences as needed
        }
        with open(USER_PREFS_FILE, "w") as f:
            json.dump(prefs, f)

    def load_prefs(self):
        """
        Load user preferences from a JSON file.
        Returns:
            dict: The loaded preferences, or an empty dict if the file does not exist.
        """
        if os.path.exists(USER_PREFS_FILE):
            with open(USER_PREFS_FILE, "r") as f:
                prefs = json.load(f)
            return prefs
        return {}

    def apply_prefs(self, prefs):
        """Apply loaded preferences to the UI."""
        if "intensity" in prefs:
            # Set the slider and device intensity
            self.intensity_slider.set(prefs["intensity"] // 263)
            self.dc.set_intensity(prefs["intensity"] // 263)
        if "stream_index" in prefs and hasattr(self, "stream_combobox"):
            self.stream_combobox.current(prefs["stream_index"])
            self.dc.set_stream(prefs["stream_index"])


if __name__ == "__main__":
    root = tk.Tk()
    app = DigitUI(root)
    root.mainloop()
