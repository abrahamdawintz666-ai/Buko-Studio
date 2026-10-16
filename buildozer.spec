
[app]
title = BuKo Studio Mobile
package.name = bukostudio
package.domain = org.buko
source.dir = .
source.include_exts = py,buko,txt,md,kv
version = 0.9.1
requirements = python3,kivy
orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
