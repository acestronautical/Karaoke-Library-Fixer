import os
import sys
import tkinter as tk
from tkinter import filedialog, scrolledtext
from fixsongs import run_fix_songs

def browse_directory(entry_field):
    directory = filedialog.askdirectory()
    entry_field.delete(0, tk.END)  # Clear the entry field
    entry_field.insert(0, directory)  # Insert the selected directory

# Function to run the script and display output
def run_script():
    dir1 = dir1_entry.get()
    dir2 = dir2_entry.get()

    if not os.path.isdir(dir1) or not os.path.isdir(dir2):
        output_text.insert(tk.END, "Please select valid directories!\n")
        return

    try:
        # Redirect stdout and stderr to output_text
        sys.stdout = TextRedirector(output_text)
        sys.stderr = TextRedirector(output_text)  # Also capture errors

        # Now any print() in fixsongs.py or the main script will go to the text widget.
        run_fix_songs(dir1, dir2)

    except Exception as e:
        output_text.insert(tk.END, f"Error: {str(e)}\n")

    finally:
        # Return stdout and stderr to default behavior (console)
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, message):
        self.widget.insert(tk.END, message)
        self.widget.see(tk.END)  # Scroll to the end

    def flush(self):
        pass  # Needed for Python 3 compatibility

# Create the main application window
app = tk.Tk()
app.title("Compuhost Library Fixer")

# Input field for first directory
tk.Label(app, text="Source Directory:").grid(row=0, column=0, padx=5, pady=5)
dir1_entry = tk.Entry(app, width=50)
dir1_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Button(app, text="Browse", command=lambda: browse_directory(dir1_entry)).grid(row=0, column=2, padx=5, pady=5)

# Input field for second directory
tk.Label(app, text="Destination Directory:").grid(row=1, column=0, padx=5, pady=5)
dir2_entry = tk.Entry(app, width=50)
dir2_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Button(app, text="Browse", command=lambda: browse_directory(dir2_entry)).grid(row=1, column=2, padx=5, pady=5)

# Run button to execute the script
run_button = tk.Button(app, text="Run", command=run_script)
run_button.grid(row=2, column=1, pady=10)

# Text area to display output
output_text = scrolledtext.ScrolledText(app, height=10, width=80)
output_text.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

# Run the main event loop
app.mainloop()
