import tkinter as tk


class DigitPopup(tk.Toplevel):
    """
    A class for creating a popup window in a Tkinter application.

    Author: Gemma McLean
    Date: June 2025
    """

    def __init__(self, parent, title, message, buttons):
        """
        Initialise the DigitPopup with a title, message, and buttons.

        Args:
            parent (tk.Tk): The parent window for the popup.
            title (str): The title of the popup window.
            message (str): The message to display in the popup.
            buttons (list of tuples): A list of button text and command pairs.
        """

        # Ensure the parent is a Tk instance
        super().__init__(parent)

        # Set the title and geometry of the popup
        self.title(title)
        self.geometry('340x120')
        self.transient(parent)
        self.lift()
        self.resizable(False, False)

        # Create and pack the message label and buttons
        label = tk.Label(self, text=message)
        label.pack(pady=20)
        button_frame = tk.Frame(self)
        button_frame.pack()

        # Create buttons based on the provided list of tuples
        for btn_text, btn_command in buttons:
            btn = tk.Button(button_frame, text=btn_text, width=10, command=btn_command)
            btn.pack(side=tk.LEFT, padx=10)

        # Center the popup on the parent window
        self.update()
        self.grab_set()
