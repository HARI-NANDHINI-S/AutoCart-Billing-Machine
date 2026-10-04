import tkinter as tk
from tkinter import messagebox
import os

# Import mode selection
from mode_select import ModeSelect

def main():
    app = ModeSelect()
    app.mainloop()

if __name__ == "__main__":
    main()