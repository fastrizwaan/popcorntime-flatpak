<p align="center">
  <img src="data/icon/org.popcorntime.NativePopcorn" width="128" alt="Native Popcorn Icon">
</p>

<h1 align="center">Native Popcorn</h1>

A native GTK4 and Libadwaita frontend for Popcorn Time, offering a modern, seamless, and deeply integrated streaming experience on Linux. Features embedded MPV playback, integrated downloading stats, and a beautiful responsive interface.

## 🚀 Features
- **Native UI**: Built with GTK4 and Libadwaita for a native GNOME experience.
- **Embedded Player**: Seamless integration with MPV for robust, hardware-accelerated playback.
- **Torrents & Streaming**: Real-time downloading stats and playback from multiple sources.

## 🛠 Installation

Native Popcorn is built and packaged using Flatpak. To install it on your system, simply run the included installation script:

```bash
./install.sh
```

This script will compile the application and install it locally using Flatpak. You can then find **Native Popcorn** in your application launcher!

## 💻 Running Directly from Source (Development)

If you'd like to test the application directly without packaging it as a Flatpak, you can run the Python source code natively:

```bash
# Navigate to the source directory
cd src/native_popcorn

# Run the main application
python3 main.py
```

*Note: Running from source requires `python3`, `gtk4`, `libadwaita`, and `mpv` to be installed on your host system.*

## 📜 License

This project is licensed under the **GPL-3.0-or-later**. See the `COPYING` file for more details.
