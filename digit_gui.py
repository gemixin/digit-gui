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
PADDING = 10
USER_PREFS_FILE = "user_prefs.json"
GREEN = "honeydew"
RED = "misty rose"


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

        # Flags to track application state
        self.gui = False  # Has the GUI been created?
        self.view_running = False  # Is the live video view running?
        self.capturing = False  # Are we currently capturing frames?

        # Initialise various settings to default values
        self.update_interval = 33
        self.local_dir = os.path.dirname(os.path.abspath(__file__))
        self.user_save_dir = self.local_dir
        self.save_dir = self.user_save_dir
        self.num_frames = 10
        self.interaction_num = 1

        # Set up the root window
        self.root.title("DIGIT GUI")
        self.root.resizable(False, False)

        # Create an empty frame to give initial window some size
        # This frame will be replaced once the GUI is set up
        self.empty_frame = tk.Frame(self.root, width=400, height=400)
        self.empty_frame.grid(row=0, column=0, padx=PADDING, pady=PADDING)
        self.empty_frame.grid_propagate(False)

        # Try and connect to DIGIT
        self.try_connect_digit()

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    # --- Initialization & Setup ---
    def setup_gui(self):
        """Set up the main GUI components after a successful connection to DIGIT."""
        # Delete empty frame to make space for the GUI
        self.empty_frame.destroy()

        # Create and place the main frames
        self.create_digit_settings_frame().grid(row=0, column=0,
                                                padx=PADDING, pady=PADDING)
        self.create_live_preview_frame().grid(row=0, column=1,
                                              padx=PADDING, pady=PADDING)
        self.create_capture_controls_frame().grid(row=1, column=1,
                                                  padx=PADDING, pady=PADDING)
        self.create_capture_settings_frame().grid(row=1, column=0,
                                                  padx=PADDING, pady=PADDING)

        # Mark the GUI as created
        self.gui = True

        # Load and apply saved user preferences
        prefs = self.load_prefs()
        self.apply_prefs(prefs)

    def create_digit_settings_frame(self):
        """
        Create the DIGIT settings frame with RGB intensity and stream combobox.
        Returns:
            tk.LabelFrame: The settings frame.
        """
        # Create a LabelFrame for whole section
        digit_settings_frame = tk.LabelFrame(self.root,
                                             text="DIGIT Settings",
                                             borderwidth=2, relief="groove")

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
        self.stream_combobox = ttk.Combobox(stream_frame,
                                            values=self.dc.get_stream_strings(),
                                            state="readonly")

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
        intensity_frame.pack(pady=PADDING, padx=PADDING)
        stream_frame.pack(pady=PADDING, padx=PADDING)

        # Return the settings frame to be placed in the main GUI
        return digit_settings_frame

    def create_live_preview_frame(self):
        """
        Create the live preview frame to display the video feed from DIGIT.
        Returns:
            tk.LabelFrame: The live preview frame.
        """
        # Create a LabelFrame for whole section
        live_preview_frame = tk.LabelFrame(self.root,
                                           text="Live Preview",
                                           borderwidth=2, relief="groove")

        # Create a label to display the video feed
        self.video_label = tk.Label(live_preview_frame)

        # Pack the label into the live_view frame with padding
        self.video_label.pack(padx=PADDING, pady=PADDING)

        # Start the live video view
        self.view_running = True
        self.update_video_frame()

        # Return the live view frame to be placed in the main GUI
        return live_preview_frame

    def create_capture_controls_frame(self):
        """
        Create the capture controls frame with button and status label.
        Returns:
            tk.LabelFrame: The capture controls frame.
        """
        # Create a LabelFrame for whole section
        capture_controls_frame = tk.LabelFrame(self.root,
                                               text="Capture Controls",
                                               borderwidth=2, relief="groove")

        # Create a button to start capturing frames
        self.save_button = tk.Button(capture_controls_frame,
                                     text="Capture",
                                     command=self.start_capture)

        # Create a label to display capture status
        self.capture_status_label = tk.Label(capture_controls_frame,
                                             text="Ready to capture",
                                             width=26, height=4,
                                             border=1, relief="sunken",
                                             bg=GREEN)

        # Pack the button and label into the capture controls frame with padding
        # Ensure button fills the width
        self.save_button.pack(pady=PADDING, padx=PADDING, fill='x')
        self.capture_status_label.pack(pady=PADDING, padx=PADDING)
        return capture_controls_frame

    def create_capture_settings_frame(self):
        # Create a LabelFrame for whole section
        capture_settings_frame = tk.LabelFrame(self.root,
                                               text="Capture Settings",
                                               borderwidth=2, relief="groove")
        # Create a frame for the save directory selection
        save_dir_frame = tk.Frame(capture_settings_frame)

        # Pack the frames into the settings frame with padding
        save_dir_frame.pack(pady=PADDING, padx=PADDING)

        return capture_settings_frame

    def select_save_directory(self):
        print("Button test")

    # --- Connection Handling ---
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

    # --- GUI State Management ---
    def enable_gui(self):
        """Enable interactive GUI elements."""
        self.intensity_slider.configure(state="normal")
        self.stream_combobox.configure(state="normal")
        self.save_button.configure(state="normal")

    def disable_gui(self):
        """Disable interactive GUI elements."""
        self.intensity_slider.configure(state="disabled")
        self.stream_combobox.configure(state="disabled")
        self.save_button.configure(state="disabled")

    # --- Preferences ---
    def save_prefs(self):
        """Save user preferences to a JSON file."""
        prefs = {
            "intensity": self.dc.get_intensity(),
            "stream_index": self.stream_combobox.current(),
            "interaction_num": self.interaction_num,
            "user_save_dir": self.user_save_dir,
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
        """
        Apply loaded preferences to the GUI.
        Args:
            prefs (dict): The preferences to apply.
        """
        if "intensity" in prefs:
            # Set the slider and device intensity
            self.intensity_slider.set(prefs["intensity"] // 263)
            self.dc.set_intensity(prefs["intensity"] // 263)
        if "stream_index" in prefs and hasattr(self, "stream_combobox"):
            # Set the stream combobox and relevant settings
            self.stream_combobox.current(prefs["stream_index"])
            self.dc.set_stream(prefs["stream_index"])
            self.refresh_update_interval()
        if "interaction_num" in prefs:
            # Set the interaction number
            # TODO: update the GUI element
            self.interaction_num = prefs["interaction_num"]
        if "user_save_dir" in prefs:
            # Set the user save directory
            # TODO: update the GUI element
            self.user_save_dir = prefs["user_save_dir"]

    # --- Live Preview & Video ---
    def update_video_frame(self):
        """Update the video frame in the live preview."""
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

                # Schedule next update based on current fps
                self.root.after(self.update_interval, self.update_video_frame)
            except Exception as e:
                # If an error occurs, disable the GUI and show a lost connection popup
                print(f"Error updating video frame: {e}")
                self.disable_gui()
                self.show_lost_connection_popup()

    def refresh_update_interval(self):
        """Refresh the live view update interval based on current fps."""
        fps = self.dc.get_fps()
        self.update_interval = 1000 // fps

    # --- User Interactions (Sliders, Combobox) ---
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
            # Refresh update interval based on new fps
            self.refresh_update_interval()

    # --- Capture Logic ---
    def start_capture(self):
        """Start capturing frames based on user settings."""
        # Disable the interactive parts of the GUI
        self.disable_gui()

        # Check user save directory exists
        if not os.path.exists(self.save_dir):
            # If it does not exist, show an error message
            self.capture_status_label.config(
                text="Capture failed:\nSave directory does not exist", bg=RED)
            # Reset after 2 seconds
            self.root.after(2000, self.capture_complete_final)
        else:
            # If the save directory exists, proceed with capture
            # Get the save directory
            self.save_dir = self.get_save_dir()
            # Reset the frame count
            self.frame_count = 0
            # Set the capture flag to True so it starts capturing frames
            self.capturing = True

    def get_save_dir(self):
        """
        Get the directory where frames will be saved based on user settings.
        Returns:
            str: The directory path where frames will be saved.
        """
        # If we are capturing multiple frames
        if self.num_frames > 1:
            # Create a folder in the save directory for this interaction
            # Get the interaction number as a string and pad it with zeros
            padded_num = self.pad_number(self.interaction_num)
            # Get the path for the interaction folder we are going to create
            interaction_folder = f"{self.user_save_dir}/interaction_{padded_num}"
            # Create the folder if it does not exist
            try:
                os.makedirs(interaction_folder, exist_ok=True)
            except Exception as e:
                print(f"Error creating directory: {e}")
            # Set the save directory to the interaction folder
            return interaction_folder
        # If we are only capturing one frame
        else:
            # Save the frame in the directory specified by the user
            return self.user_save_dir

    def capture_frame(self, frame):
        # Increment the frame count
        self.frame_count += 1
        # Update the capture status label with the current frame count
        self.capture_status_label.config(
            text=f"Capturing frame {self.frame_count}/{self.num_frames}")
        # Save the frame to a file
        self.save_frame_file(frame)
        # Check if we have captured enough frames
        if self.frame_count >= self.num_frames:
            # End the capture process
            self.capture_complete()

    def save_frame_file(self, frame):
        # Save the frame
        # If we are capturing multiple frames, use the frame count to name the file
        if self.num_frames > 1:
            fname = f"frame_{self.pad_number(self.frame_count)}"
        # If we are only capturing one frame, use the interaction number to name the file
        else:
            fname = f"interaction_{self.pad_number(self.interaction_num)}"
        # Save the frame as a JPEG file in the save directory
        try:
            cv2.imwrite(f"{self.save_dir}/{fname}.jpg", frame)
        except Exception as e:
            print(f"Error saving file: {e}")

    def capture_complete(self):
        """Start completion of the capture process."""
        # Set the capture flag to False so it stops capturing frames
        self.capturing = False
        # Reset the frame count
        self.frame_count = 0
        # Increment the interaction number
        self.interaction_num += 1
        # After a delay, call the capture complete message
        self.root.after(500, self.capture_complete_message)

    def capture_complete_message(self):
        """Show a message indicating capture completion."""
        # Set the capture status label
        self.capture_status_label.config(text="Capture complete!")
        # After a delay, call the final completion function
        self.root.after(1000, self.capture_complete_final)

    def capture_complete_final(self):
        """Reset the capture process."""
        # Reset the capture status label
        self.capture_status_label.config(text="Ready to capture", bg=GREEN)
        # Enable the interactive parts of the GUI
        self.enable_gui()

    # --- Utility ---
    def pad_number(self, num):
        """
        Pad a number with leading zeros to ensure it is 3 digits.
        Args:
            num (int): The number to pad.
        Returns:
            str: The padded number as a string.
        """
        return str(num).zfill(3)


# Main entry point for the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DigitGUI(root)
    root.mainloop()
