[app]
title = MediaFolder Pro
package.name = mediafolderpro
package.domain = one.apizutool
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 2.0.0
requirements = python3,kivy==2.3.0,requests,beautifulsoup4,pillow,certifi,charset-normalizer,idna,urllib3,soupsieve
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.icon.filename = %(source.dir)s/icon.png
android.presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #111111
android.gradle_dependencies = 
android.enable_androidx = True
p4a.branch = master
log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
