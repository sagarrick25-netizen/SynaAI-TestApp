[app]

title = SynaAI Test App
package.name = synaai
package.domain = org.sagar.ai

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = WRITE_SETTINGS,MODIFY_AUDIO_SETTINGS

# Stable Android config
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# Auto accept SDK licenses
android.accept_sdk_license = True

# Stable python-for-android branch
p4a.branch = master

# Prevent problematic AndroidX auto-updates
android.enable_androidx = False

# App appearance
presplash_color = #111111
