# MediaFolder Pro

<p align="center">
  <img src="https://apizutool.one/images/logoz/dwnld/mediafire.png" width="80" alt="MediaFolder Pro logo"/>
</p>

<p align="center">
  <strong>A fast, full-featured MediaFire folder downloader for Windows, Linux, macOS, and Android.</strong>
</p>

<p align="center">
  <a href="https://github.com/Hexadecinull/MediaFolderPro/releases"><img src="https://img.shields.io/github/v/release/Hexadecinull/MediaFolderPro?style=flat-square" alt="Latest release"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square" alt="License"/></a>
  <a href="https://github.com/Hexadecinull/MediaFolderPro/actions"><img src="https://img.shields.io/github/actions/workflow/status/Hexadecinull/MediaFolderPro/ci.yml?style=flat-square" alt="CI"/></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS%20%7C%20Android-lightgrey?style=flat-square" alt="Platforms"/>
</p>

---

## Features

- **Recursive folder tree** — browses and fetches the full structure of any public MediaFire folder
- **Selective download** — toggle individual files or entire folders with checkboxes; selected size updates live
- **Parallel downloads** — 3 concurrent threads for maximum throughput
- **Real-time speed graph** — animated KB/s graph with ETA, elapsed time, peak speed, and remaining size
- **Pause / Resume / Abort** — full download lifecycle control
- **Failed file tracking** — failed downloads are collected and can be retried individually or all at once
- **Live console** — timestamped, colour-coded log of every fetch, download, and error event
- **Fetch animation** — shimmer progress indicator on the fetch button with an inline stop control
- **Dark & Light theme** — toggle at any time without restarting
- **Android version** — native touch UI built with Kivy, compilable to APK with Buildozer
- **Saves last download path** — persisted across sessions via `mediafolder_settings.json`
- **GPL-3.0 licensed**

---

## Screenshots

Soon

---

## Requirements

### Desktop (Windows / Linux / macOS)

| Dependency | Version |
|---|---|
| Python | 3.10+ |
| tkinter | bundled with Python |
| requests | ≥ 2.28 |
| beautifulsoup4 | ≥ 4.12 |
| Pillow | ≥ 10.0 |

Install dependencies:

```bash
pip install requests beautifulsoup4 Pillow
```

### Android

| Dependency | Notes |
|---|---|
| Python | 3.10+ |
| Kivy | 2.3.0 |
| Buildozer | latest |
| requests, beautifulsoup4 | auto-bundled by Buildozer |

See [BUILD_ANDROID.md](BUILD_ANDROID.md) for the full Android build guide.

---

## Installation & Running

### Desktop

```bash
# Clone the repo
git clone https://github.com/Hexadecinull/MediaFolderPro.git
cd MediaFolderPro

# Install dependencies
pip install -r requirements.txt

# Run
python mediafolder.py
```

### Android (debug APK)

```bash
# Rename entry point
cp mediafolder_android.py main.py

# Build (first run downloads NDK/SDK — takes 15–30 min)
buildozer android debug

# Install on device
buildozer android deploy run
```

Full Android build instructions: [BUILD_ANDROID.md](BUILD_ANDROID.md)

---

## Usage

1. Paste a MediaFire folder URL into **Source URL** (e.g. `https://www.mediafire.com/folder/abc123/MyFolder`)
2. Choose a **Download Location** with the Browse button
3. Click **FETCH CONTENT** — the file tree populates with all folders and files
4. Use the checkboxes in the **Selection** column to toggle files; the sidebar updates selected size live
5. Click **START DOWNLOAD** — progress bars, speed graph, ETA, and the console all update in real time
6. Use **PAUSE / RESUME** or **STOP** as needed
7. If any files fail, **VIEW FAILED FILES** becomes available — retry individually or all at once

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

Please keep code style consistent with the existing codebase (no inline comments, clean method names, threading safety).

---

## License

MediaFolder Pro is released under the **GNU General Public License v3.0**.
See [LICENSE](LICENSE) for full terms.

---

## Author

**SSMG4** — [Hexadecinull](https://github.com/Hexadecinull)
