[app]
title = Recibo Software
package.name = recibosoftware
package.domain = org.robsoncadete
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.8
requirements = python3,kivy,sqlite3,urllib3,openssl
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
