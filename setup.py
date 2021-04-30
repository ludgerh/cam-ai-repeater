from cx_Freeze import setup, Executable
includefiles = ['ffmpeg', 'c_repeater.cfg', 'icons']

setup(
  name = "Repeater driver for CAM-AI",
  version = "1.0",
  description = "Connecting your cameras with the CAM-AI server",
  author = 'www.cam-ai.de',
  options = {'build_exe': {'include_files':includefiles},
    'bdist_msi': {'all_users':True, 'install_icon':'icons/windows.ico'}}, 
  executables = [Executable("c_repeater.py", shortcutName="CAM-AI Repeater", shortcutDir="DesktopFolder", icon="icons/windows.ico"), Executable("c_repeater_cam.py")]
)
