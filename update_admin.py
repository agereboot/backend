import os

path = r"d:\AgeReboot\AgeReboot\Reboot\Reboot_App\admin.py"
with open(path, "r") as f:
    content = f.read()

# Update imports
if "EMRAllergy" not in content:
    content = content.replace("CarePlan\n)", "CarePlan,\n    EMRAllergy, DiagnosticOrder\n)")

with open(path, "w") as f:
    f.write(content)

print("Updated admin.py successfully")
