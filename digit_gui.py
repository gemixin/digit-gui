import tkinter as tk
from tkinter import ttk, filedialog
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
MAX_NUM_FRAMES = 600
MAX_INTERACTION_NUM = 9999
MAX_COUNTDOWN_SECS = 10


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
        self.num_frames = 1
        self.interaction_num = 1
        self.countdown_secs = 1
        self.countdown = False

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

        # Configure grid weights to allow horizontal expansion
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # Create and place the main frames
        self.create_settings_frame().grid(row=0, column=0,
                                          padx=PADDING, pady=PADDING, sticky="nsew")
        self.create_live_preview_frame().grid(row=0, column=1, rowspan=2,
                                              padx=PADDING, pady=PADDING, sticky="nsew")
        self.create_capture_controls_frame().grid(row=1, column=0,
                                                  padx=PADDING, pady=PADDING, sticky="nsew")
        self.create_save_dir_frame().grid(row=2, column=0, columnspan=2,
                                          padx=PADDING, pady=PADDING, sticky="ew")

        # Mark the GUI as created
        self.gui = True

        # Load and apply saved user preferences
        prefs = self.load_prefs()
        self.apply_prefs(prefs)

    def create_settings_frame(self):
        """
        Create the settings frame with various components for user adjustable settings.
        Returns:
            tk.LabelFrame: The settings frame.
        """
        # Create a LabelFrame for whole section
        settings_frame = tk.LabelFrame(self.root,
                                       text="Settings",
                                       borderwidth=2, relief="groove")

        # --- RGB intensity components ---
        # Create the label
        intensity_label = tk.Label(settings_frame, text="RGB Intensity")

        # Get the min and max intensity values from the DigitController
        min_intensity = self.dc.get_min_intensity()
        max_intensity = self.dc.get_max_intensity()

        # Create the slider with the range of min to max intensity
        self.intensity_slider = tk.Scale(settings_frame,
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
        # ---------------------------------

        # --- Stream mode components ---
        # Create the label
        stream_label = tk.Label(settings_frame, text="Stream Mode")

        # Create the combobox with stream options from DigitController
        self.stream_combobox = ttk.Combobox(settings_frame,
                                            width=10,
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
        # ---------------------------------

        # --- Number of frames components ---
        # Create label
        num_frames_label = tk.Label(settings_frame,
                                    text="Number of Frames to Capture")

        # Create the Spinbox to allow user to select number of frames
        num_frames_validator = (self.root.register(self.validate_num_frames), "%P")
        self.num_frames_spinbox = tk.Spinbox(
            settings_frame,
            width=4,
            from_=1, to=MAX_NUM_FRAMES,
            validate="key",
            validatecommand=num_frames_validator
        )
        # ---------------------------------

        # --- Interaction number components ---
        # Create label
        interaction_num_label = tk.Label(settings_frame,
                                         text="Interaction Number")
        # Create a Spinbox to allow user to select interaction number
        interaction_num_validator = (self.root.register(
            self.validate_interaction_num), "%P")
        self.interaction_num_spinbox = tk.Spinbox(
            settings_frame,
            width=4,
            from_=1, to=MAX_INTERACTION_NUM,
            validate="key",
            validatecommand=interaction_num_validator
        )
        # ---------------------------------

        # --- Countdown seconds components ---
        # Create label
        countdown_secs_label = tk.Label(settings_frame,
                                        text="Countdown Seconds")
        # Create a Spinbox to allow user to select interaction number
        countdown_secs_validator = (self.root.register(
            self.validate_countdown_secs), "%P")
        self.countdown_secs_spinbox = tk.Spinbox(
            settings_frame,
            width=4,
            from_=1, to=MAX_COUNTDOWN_SECS,
            validate="key",
            validatecommand=countdown_secs_validator
        )
        # ---------------------------------

        # Place the frames into the settings frame, aligning them to the left
        intensity_label.grid(row=0, column=0, sticky="ws",
                             padx=PADDING, pady=PADDING)  # Align to bottom of slider
        self.intensity_slider.grid(row=0, column=1, sticky="w",
                                   padx=PADDING/2, pady=PADDING)
        stream_label.grid(row=1, column=0, sticky="w",
                          padx=PADDING, pady=PADDING)
        self.stream_combobox.grid(row=1, column=1, sticky="w",
                                  padx=PADDING/2, pady=PADDING)
        num_frames_label.grid(row=2, column=0, sticky="w",
                              padx=PADDING, pady=PADDING)
        self.num_frames_spinbox.grid(row=2, column=1, sticky="w",
                                     padx=PADDING/2, pady=PADDING)
        interaction_num_label.grid(row=3, column=0, sticky="w",
                                   padx=PADDING, pady=PADDING)
        self.interaction_num_spinbox.grid(row=3, column=1, sticky="w",
                                          padx=PADDING/2, pady=PADDING)
        countdown_secs_label.grid(row=4, column=0, sticky="w",
                                  padx=PADDING, pady=PADDING)
        self.countdown_secs_spinbox.grid(row=4, column=1, sticky="w",
                                         padx=PADDING/2, pady=PADDING)

        # Return the settings frame to be placed in the main GUI
        return settings_frame

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

        # Center the label in the live_view frame
        self.video_label.pack(padx=PADDING, pady=PADDING,
                              anchor="center", expand=True)

        # Start the live video view
        self.view_running = True
        self.update_video_frame()

        # Return the live view frame to be placed in the main GUI
        return live_preview_frame

    def create_capture_controls_frame(self):
        """
        Create the capture controls frame with label and button.
        Returns:
            tk.LabelFrame: The capture controls frame.
        """
        # Create a LabelFrame for whole section
        capture_controls_frame = tk.LabelFrame(self.root,
                                               text="Capture Controls",
                                               borderwidth=2, relief="groove")

        # Create a label to display capture status
        self.capture_status_label = tk.Label(capture_controls_frame,
                                             text="Ready to capture",
                                             width=30, height=4,
                                             border=1, relief="sunken",
                                             bg=GREEN)

        # Create a button to start capturing frames
        self.save_button = tk.Button(capture_controls_frame,
                                     text="Capture",
                                     command=self.start_capture)

        # Create a checkbox to enable countdown before capturing
        # Create a BooleanVar to track countdown checkbox state
        self.countdown_var = tk.BooleanVar(value=False)
        # Update the countdown attribute when the checkbox is toggled
        self.countdown_checkbox = tk.Checkbutton(
            capture_controls_frame,
            text="Countdown",
            variable=self.countdown_var,
            command=lambda: setattr(self, "countdown", self.countdown_var.get())
        )

        # Pack the frames and elements into the capture controls frame with padding
        self.capture_status_label.pack(pady=PADDING, padx=PADDING, fill="x")
        self.countdown_checkbox.pack(side=tk.LEFT, pady=PADDING, padx=PADDING, anchor="w")
        # Ensure button fills the remaining width
        self.save_button.pack(pady=PADDING, padx=PADDING, fill="x")

        # Return the capture controls frame to be placed in the main GUI
        return capture_controls_frame

    def create_save_dir_frame(self):
        """
        Create the save directory frame with entry box and button.
        Returns:
            tk.LabelFrame: The save directory frame.
        """
        # Create a LabelFrame for whole section
        save_dir_frame = tk.LabelFrame(self.root,
                                       text="Save Directory",
                                       borderwidth=2, relief="groove")

        # Create an entry box to display the save directory
        self.save_dir_entry = tk.Entry(save_dir_frame)

        # Set the initial save directory to the user save directory
        self.save_dir_entry.insert(0, self.user_save_dir)

        # Make readonly by default
        self.save_dir_entry.configure(state="disabled")

        # Create a button to select the save directory
        self.save_dir_button = tk.Button(save_dir_frame,
                                         text="Select Directory",
                                         command=self.select_save_directory)

        # Pack the components into the save directory frame with padding
        # Ensure entry fills the width
        self.save_dir_entry.grid(row=0, column=0,
                                 sticky="ew",
                                 padx=PADDING, pady=PADDING)
        self.save_dir_button.grid(row=0, column=1,
                                  padx=PADDING, pady=PADDING)
        save_dir_frame.columnconfigure(0, weight=1)

        return save_dir_frame

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
        self.num_frames_spinbox.configure(state="normal")
        self.interaction_num_spinbox.configure(state="normal")
        self.countdown_secs_spinbox.configure(state="normal")
        self.save_dir_button.configure(state="normal")

    def disable_gui(self):
        """Disable interactive GUI elements."""
        self.intensity_slider.configure(state="disabled")
        self.stream_combobox.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.num_frames_spinbox.configure(state="disabled")
        self.interaction_num_spinbox.configure(state="disabled")
        self.countdown_secs_spinbox.configure(state="disabled")
        self.save_dir_button.configure(state="disabled")

    # --- Preferences ---
    def save_prefs(self):
        """Save user preferences to a JSON file."""
        prefs = {
            "intensity": self.dc.get_intensity(),
            "stream_index": self.stream_combobox.current(),
            "num_frames": self.num_frames,
            "interaction_num": self.interaction_num,
            "countdown_secs": self.countdown_secs,
            "countdown": self.countdown,
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
        if "num_frames" in prefs:
            # Set the number of frames to capture
            self.num_frames = prefs["num_frames"]
            self.refresh_num_frames_spinbox()
        if "interaction_num" in prefs:
            # Set the interaction number
            self.interaction_num = prefs["interaction_num"]
            self.refresh_interaction_num_spinbox()
        if "countdown_secs" in prefs:
            # Set the countdown seconds
            self.countdown_secs = prefs["countdown_secs"]
            self.refresh_countdown_secs_spinbox()
        if "countdown" in prefs:
            # Set the countdown toggle
            self.countdown = prefs["countdown"]
            self.countdown_var.set(self.countdown)
        if "user_save_dir" in prefs:
            # Set the user save directory
            self.user_save_dir = prefs["user_save_dir"]
            self.refresh_save_dir_entry()

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

    # --- User Interactions ---
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

    def select_save_directory(self):
        """
        Open a file dialog to select the save directory and update the entry box.
        """
        # Open a directory selection dialog
        selected_dir = filedialog.askdirectory(initialdir=self.user_save_dir,
                                               title="Select Save Directory")
        # If a directory was selected
        if selected_dir:
            # Update the user save directory
            self.user_save_dir = selected_dir
            # Update the entry box with the new save directory
            self.refresh_save_dir_entry()

    def refresh_save_dir_entry(self):
        """Refresh the save directory entry box with the current user save directory."""
        # Allow temporary editing of the save directory entry
        self.save_dir_entry.configure(state="normal")
        # Update the entry box with the new save directory
        self.save_dir_entry.delete(0, tk.END)
        self.save_dir_entry.insert(0, self.user_save_dir)
        # Disable the entry box again
        self.save_dir_entry.configure(state="disabled")

    def validate_num_frames(self, value):
        """
        Validate the input for the number of frames spinbox, and if valid, update the
        number of frames.
        Args:
            value (str): The value to validate.
        Returns:
            bool: True if valid, False otherwise.
        """
        # Allow empty input for editing
        if value == "":
            return True
        if value.isdigit():
            # Convert the value to an integer
            num = int(value)
            # Check if the number is within the valid range
            if 1 <= num <= MAX_NUM_FRAMES:
                # If valid, update the number of frames
                self.num_frames = num
                return True
        # If not valid, return False
        return False

    def validate_interaction_num(self, value):
        """
        Validate the input for the interaction number spinbox and if valid, update the
        interaction number.
        Args:
            value (str): The value to validate.
        Returns:
            bool: True if valid, False otherwise.
        """
        # Allow empty input for editing
        if value == "":
            return True
        if value.isdigit():
            # Convert the value to an integer
            num = int(value)
            # Check if the number is within the valid range
            if 1 <= num <= MAX_INTERACTION_NUM:
                # If valid, update the interaction number
                self.interaction_num = num
                return True
        # If not valid, return False
        return False

    def validate_countdown_secs(self, value):
        """
        Validate the input for the countdown seconds spinbox and if valid, update the
        countdown seconds.
        Args:
            value (str): The value to validate.
        Returns:
            bool: True if valid, False otherwise.
        """
        # Allow empty input for editing
        if value == "":
            return True
        if value.isdigit():
            # Convert the value to an integer
            num = int(value)
            # Check if the number is within the valid range
            if 1 <= num <= MAX_COUNTDOWN_SECS:
                # If valid, update the countdown seconds
                self.countdown_secs = num
                return True
        # If not valid, return False
        return False

    def refresh_num_frames_spinbox(self):
        """Refresh the number of frames spinbox with the current number of frames."""
        self.num_frames_spinbox.delete(0, "end")
        self.num_frames_spinbox.insert(0, self.num_frames)

    def refresh_interaction_num_spinbox(self):
        """Refresh the interaction number spinbox with the current interaction number."""
        self.interaction_num_spinbox.delete(0, "end")
        self.interaction_num_spinbox.insert(0, self.interaction_num)

    def refresh_countdown_secs_spinbox(self):
        """Refresh the countdown seconds spinbox with the current countdown seconds."""
        self.countdown_secs_spinbox.delete(0, "end")
        self.countdown_secs_spinbox.insert(0, self.countdown_secs)

    # --- Capture Logic ---
    def start_capture(self):
        """Start capturing frames based on user settings."""
        # Disable the interactive parts of the GUI
        self.disable_gui()

        # Always get the current save directory for this capture
        self.save_dir = self.get_save_dir()

        # Check user save directory exists
        if not os.path.exists(self.save_dir):
            # If it does not exist, show an error message
            print(self.save_dir)
            self.capture_status_label.config(
                text="Capture failed:\nSave directory does not exist", bg=RED)
            # Reset after 2 seconds
            self.root.after(2000, self.capture_complete_final)
        # If the save directory exists, proceed with capture
        else:
            # If countdown is enabled, start the countdown
            if (self.countdown):
                self.start_countdown(self.countdown_secs)
            # If countdown is not enabled, start capturing immediately
            else:
                # Reset the frame count
                self.frame_count = 0
                # Set the capture flag to True so it starts capturing frames
                self.capturing = True

    def start_countdown(self, seconds):
        """
        Start a countdown timer for the specified number of seconds.
        Args:
            seconds (int): The number of seconds to count down from.
        """
        # Update the capture status label with the countdown
        self.capture_status_label.config(
            text=f"Capturing in {seconds} seconds...")
        # If there are more than 0 seconds left, schedule the next countdown
        if seconds > 0:
            self.root.after(1000, lambda: self.start_countdown(seconds - 1))
        else:
            # When countdown reaches 0, start capturing frames
            self.frame_count = 0
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
        """
        Capture a single frame and save it to the specified directory.
        Args:
            frame (numpy.ndarray): The frame to capture.
        """
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
        """
        Save the captured frame to a file in the specified save directory.
        Args:
            frame (numpy.ndarray): The frame to save.
        """
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
        if self.interaction_num < MAX_INTERACTION_NUM:
            # Temporarily enable the interaction number spinbox for editing
            self.interaction_num_spinbox.configure(state="normal")
            # Increment the interaction number
            self.interaction_num += 1
            # Refresh the interaction number spinbox to show the new value
            self.refresh_interaction_num_spinbox()
            # Disable the spinbox again
            self.interaction_num_spinbox.configure(state="disabled")
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
        Pad a number with leading zeros to ensure it is 4 digits.
        Args:
            num (int): The number to pad.
        Returns:
            str: The padded number as a string.
        """
        return str(num).zfill(4)


# Main entry point for the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DigitGUI(root)
    root.mainloop()
