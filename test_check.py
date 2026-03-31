import subprocess
result = subprocess.run([r"d:\AgeReboot\AgeReboot\Reboot\.venv\Scripts\python.exe", "manage.py", "check"], capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("STDERR:")
print(result.stderr)
