# KeyCast

A modern, minimalist, always-on-top keyboard and mouse visualizer for Windows, perfect for screencasts, presentations, and tutorials.

<img width="529" height="92" alt="image" src="https://github.com/user-attachments/assets/0ac46b94-2183-4d38-9b49-1abbcc5900a7" />

---

## ✨ Features

* **Real-time Display**: Instantly shows keyboard presses, including shortcuts with modifiers (Ctrl, Alt, Shift).
* **Mouse Visualization**: Clearly indicates left, middle, and right mouse clicks, with a special blink effect for scrolling.
* **Modern & Minimalist**: A clean, borderless design that looks great on any desktop.
* **Always-On-Top**: Stays visible over your other applications.
* **Fully Draggable**: Click and drag anywhere on the display to reposition it.
* **Intelligent Clearing**: Keystrokes are cleared automatically to save space, and the display fades out after a period of inactivity.
* **System Tray Management**: Runs discreetly in the system tray with options to Show/Hide or Exit the application.

---

## 💻 How to Use

### For Users

1.  Go to the [Releases page](https://github.com/your-username/keycast/releases) of this repository.
2.  Download the latest `KeyCast.exe` file From [Here](https://github.com/akasumitlamba/KeyCast/releases/download/v1.0.0/KeyCast.exe).
3.  Run the executable. No installation is needed!

**Important:** For the app to capture all keyboard and mouse events, you may need to **right-click `KeyCast.exe` and select "Run as administrator"**.

The app will appear on your screen and can be managed from its icon in the system tray ( ^ icon next to your clock).

### For Developers (Building from Source)

Follow these steps to build the application yourself.

#### **1. Prerequisites**
* Python 3.8+
* Git

#### **2. Setup**
```bash
# Clone the repository
git clone [https://github.com/your-username/keycast.git](https://github.com/your-username/keycast.git)
cd keycast

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install the required dependencies
pip install -r requirements.txt
```
*(You will need to create a `requirements.txt` file containing `pynput`, `pillow`, and `pystray`)*

#### **3. Running the App**
```bash
# Run the script directly for testing
python ShowKeys.py
```

#### **4. Building the Executable**
Make sure you have an icon file named `KeyCast.ico` in the root directory. Then, run the PyInstaller command:
```bash
pyinstaller --onefile --windowed --name="KeyCast" --icon="KeyCast.ico" --add-data "KeyCast.ico;." ShowKeys.py
```
Your final `KeyCast.exe` will be in the `dist` folder.

---

## 🎨 Configuration

You can easily customize the look and feel of KeyCast by editing the configuration variables at the top of the `ShowKeys.py` script before building. Change colors, fonts, sizes, and delays to match your style.

---

## 📜 License

This project is licensed under the MIT License.
