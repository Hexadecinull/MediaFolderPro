# Building MediaFolder Pro for Android

## What you need

- A Linux machine or VM (Ubuntu 22.04 recommended — buildozer does not support Windows natively)
- Python 3.10+
- ~8 GB free disk space (first build downloads the Android NDK/SDK)

---

## Step 1 — Install system dependencies

```bash
sudo apt update
sudo apt install -y \
    git zip unzip openjdk-17-jdk python3-pip \
    autoconf libtool pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev libtinfo5 \
    cmake libffi-dev libssl-dev
```

---

## Step 2 — Install buildozer

```bash
pip install --upgrade buildozer cython
```

---

## Step 3 — Set up your project folder

Create a folder and place these files inside it:

```
my_project/
├── main.py              ← rename mediafolder_android.py to main.py
├── buildozer.spec
├── icon.png             ← 512x512 app icon (optional but recommended)
└── presplash.png        ← splash screen image (optional)
```

> **Important:** Buildozer always looks for `main.py` as the entry point.
> Rename `mediafolder_android.py` → `main.py` before building.

---

## Step 4 — Build the APK

```bash
cd my_project
buildozer android debug
```

The first build takes **15–30 minutes** as it downloads the Android NDK, SDK, and compiles all Python dependencies. Subsequent builds are much faster.

The output APK will be at:

```
my_project/bin/MediaFolderPro-2.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

---

## Step 5 — Install on your device

Enable **Developer Options** and **USB Debugging** on your Android device, then:

```bash
buildozer android deploy run
```

Or transfer the APK file manually and install it (you may need to allow "Install from unknown sources" in your device settings).

---

## Building a release APK (signed)

For a proper release build (required for Play Store):

```bash
buildozer android release
```

You will then need to sign it with `jarsigner` or Android Studio. See:
https://developer.android.com/studio/publish/app-signing

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SDK not found` | Run `buildozer android debug` once — it auto-downloads |
| `JAVA_HOME not set` | `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` |
| Permission denied on /sdcard | Android 11+ requires `MANAGE_EXTERNAL_STORAGE` — grant it in App Settings |
| Build fails on `cython` | `pip install --upgrade cython==0.29.37` |
| App crashes on launch | Run `adb logcat | grep python` to see the Python traceback |

---

## Using WSL2 on Windows

If you are on Windows, you can build via WSL2:

1. Install WSL2 with Ubuntu 22.04 from the Microsoft Store
2. Follow all steps above inside the WSL2 terminal
3. The APK will appear in `\\wsl$\Ubuntu\home\<user>\my_project\bin\`

---

## Minimum Android version

The app targets **Android 5.0 (API 21)** and above, which covers 99%+ of active devices.
