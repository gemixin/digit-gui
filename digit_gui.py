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

# Constants
DEFAULT_PADDING = 10
USER_PREFS_FILE = "digit_prefs.json"


class DigitGUI:
    def __init__(self, root):
        """
        Initialise the Digit GUI application.
        Args:
            root (tk.Tk): The root window for the application.
        """
        # Initialise DigitController and root window
        self.dc = None
        self.root = root

        # Track if the GUI has been created
        self.gui = False
        # Track if the live video view is running
        self.view_running = False
        # Set the update interval for video frames
        self.update_interval = 33  # Default to ~30 FPS if not set

        # TODO: Remove these temp settings
        self.save_root_dir = 'images'
        self.save_dir = 'images'
        self.num_frames = 50
        self.interaction_num = 1
        self.capturing = False
        self.frame_count = 0

        # Set up the root window
        self.root.title("DIGIT GUI")
        self.root.geometry("640x480")
        self.root.resizable(False, False)

        # Try and connect to DIGIT
        self.try_connect_digit()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def close_app(self):
        """Handle the application close event."""
        # If the GUI has been created, save user preferences
        if self.gui:
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
            # If connected, set up the GUI
            self.setup_gui()

    def setup_gui(self):
        """Set up the main GUI components after a successful connection to DIGIT."""
        # Create and place the main frames
        self.create_digit_settings_frame().grid(row=0, column=0,
                                                padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
        self.create_live_preview_frame().grid(row=0, column=1,
                                              padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
        # Create a button underneath the preview frame to save the current frame
        self.save_button = tk.Button(self.root, text="Capture",
                                command=self.test_save)
        self.save_button.grid(row=1, column=1,
                         padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)
        
        # Create a label to display capture status
        self.capture_status_label = tk.Label(self.root, text="Ready to capture")
        self.capture_status_label.grid(row=1, column=0,
                                       padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)

        # Mark the GUI as created
        self.gui = True

        # Load and apply saved user preferences
        prefs = self.load_prefs()
        self.apply_prefs(prefs)

    def test_save(self):
        if self.num_frames > 1:
            # Create a folder in the save directory for this interaction
            inum = self.pad_number(self.interaction_num)
            interaction_folder = f"{self.save_root_dir}/interaction_{inum}"
            os.makedirs(interaction_folder, exist_ok=True)
            self.save_dir = interaction_folder
        else:
            self.save_dir = self.save_root_dir
        self.disable_gui()
        self.capturing = True
        self.frame_count = 0

    def pad_number(self, num):
        """
        Pad a number with leading zeros to ensure it is 3 digits.
        Args:
            num (int): The number to pad.
        Returns:
            str: The padded number as a string.
        """
        return str(num).zfill(3)
    
    def create_digit_settings_frame(self):
        """
        Create the DIGIT settings frame with RGB intensity and stream controls.
        Returns:
            tk.LabelFrame: The settings frame containing the controls.
        """
        # Create a LabelFrame for whole section
        digit_settings_frame = tk.LabelFrame(
            self.root, text="DIGIT Settings", borderwidth=2, relief="groove")

        # --- RGB intensity components ---
        # Create frame for intensity label and slider elements
        intensity_frame = tk.Frame(digit_settings_frame)

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
        stream_frame = tk.Frame(digit_settings_frame)

        # Create the label
        stream_label = tk.Label(stream_frame, text="Stream Mode:")

        # Create the combobox with stream options from DigitController
        self.stream_combobox = ttk.Combobox(
            stream_frame,
            values=self.dc.get_stream_strings(),
            state="readonly",
        )

        # There is a weird bug where the output glitches a little on QVGA mode
        # Fix this bug by switching to VGA mode for a split second first
        self.dc.set_stream(0)
        # Then switch back to the default mode (QVGA 60fps)
        self.dc.set_stream(2)

        # Set initial combobox value based on default stream mode and fps
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

        # Return the settings frame to be placed in the main GUI
        return digit_settings_frame

    def create_live_preview_frame(self):
        """
        Create the live preview frame to display the video feed from DIGIT.
        Returns:
            tk.LabelFrame: The live preview frame containing the video feed.
        """
        # Create a LabelFrame for whole section
        live_preview_frame = tk.LabelFrame(
            self.root, text="Live Preview", borderwidth=2, relief="groove")

        # Create a label to display the video feed
        self.video_label = tk.Label(live_preview_frame)

        # Pack the frame into the live_view frame with padding
        self.video_label.pack(padx=DEFAULT_PADDING, pady=DEFAULT_PADDING)

        # Start the live video view
        self.view_running = True
        self.update_video_frame()

        # Return the live view frame to be placed in the main GUI
        return live_preview_frame

    def update_video_frame(self):
        """ Update the video frame in the live preview."""
        # If the live view is running
        if self.view_running:
            try:
                # Get the current video frame from DIGIT
                frame = self.dc.get_frame()
                if frame is not None:
                    # If capturing frames, save the current frame
                    if self.capturing:
                        self.capture_frame(frame)
                    # Display the current frame in the video label
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
                # If an error occurs, disable the GUI and show a lost connection popup
                print(f"Error updating video frame: {e}")
                self.disable_gui()
                self.show_lost_connection_popup()

    def capture_complete(self):
        # Stop capturing and reset frame count
        self.capturing = False
        self.frame_count = 0
        self.interaction_num += 1
        # Add delay of 1 second before resetting the label
        self.root.after(1000, lambda: self.capture_status_label.config(text="Ready to capture"))
        self.enable_gui()

    def capture_frame(self, frame):
        # Increment the frame count
        self.frame_count += 1
        self.capture_status_label.config(text=f"Capturing frame {self.frame_count}/{self.num_frames}")
        if self.num_frames > 1:
            fname = f"frame_{self.pad_number(self.frame_count)}"
        else:
            fname = f"interaction_{self.pad_number(self.interaction_num)}"            
        cv2.imwrite(
            f"{self.save_dir}/{fname}.jpg", frame)
        # Check if we have captured enough frames
        if self.frame_count >= self.num_frames:
            self.capture_complete()

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
            # Refresh values relating to fps
            self.refresh_update_interval()
            # TODO Refresh the capture FPS calculation based on new fps

    def refresh_update_interval(self):
        """Refresh the live view update interval based on current fps."""
        fps = self.dc.get_fps()
        self.update_interval = 1000 // fps

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

    def disable_gui(self):
        """Disable all GUI elements in the root window to prevent further interaction."""
        # Disable all widgets in the root window
        # disable slider
        if hasattr(self, 'intensity_slider'):
            self.intensity_slider.configure(state="disabled")
        if hasattr(self, 'stream_combobox'):
            self.stream_combobox.configure(state="disabled")
        if hasattr(self, 'save_button'):
            self.save_button.configure(state="disabled")
    
    def enable_gui(self):
        """Enable all GUI elements in the root window to allow interaction."""
        # Enable all widgets in the root window
        if hasattr(self, 'intensity_slider'):
            self.intensity_slider.configure(state="normal")
        if hasattr(self, 'stream_combobox'):
            self.stream_combobox.configure(state="normal")
        if hasattr(self, 'save_button'):
            self.save_button.configure(state="normal")


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
        """Apply loaded preferences to the GUI."""
        if "intensity" in prefs:
            # Set the slider and device intensity
            self.intensity_slider.set(prefs["intensity"] // 263)
            self.dc.set_intensity(prefs["intensity"] // 263)
        if "stream_index" in prefs and hasattr(self, "stream_combobox"):
            # Set the stream combobox and relevant settings
            self.stream_combobox.current(prefs["stream_index"])
            self.dc.set_stream(prefs["stream_index"])
            self.refresh_update_interval()


# Main entry point for the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DigitGUI(root)
    root.mainloop()
