import os
import django
import random
from datetime import datetime, timezone, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Reboot.settings")
django.setup()

from Reboot_App.models import UserProfile, Department, LeaveBalance, Company
from django.contrib.auth.models import User

DEPARTMENTS = ["Engineering", "Product", "Design", "Marketing", "Sales", "Clinical"]
LEVELS = ["executive", "vp", "manager", "associate"]

def seed_org_chart():
    print("📈 Ensuring Departments exist...")
    comp, _ = Company.objects.get_or_create(name="AgeReboot Demo Corp")
    
    dept_objs = {}
    for d in DEPARTMENTS:
        dept, _ = Department.objects.get_or_create(name=d, defaults={'company': comp})
        dept_objs[d] = dept
        
    print("🧹 Cleaning previous dummy org charts (preserving base users)...")
    LeaveBalance.objects.all().delete()
    
    users = list(User.objects.filter(username__startswith='hps_mock'))
    if not users:
        print("❌ No dummy users found! Run seed_hps_analytics.py first.")
        return
        
    print("🌳 Structuring the Organizational Tree...")
    executives = users[:2]
    vps = users[2:6]
    managers = users[6:15]
    associates = users[15:40]
    
    # Execs
    for u in executives:
        p = u.profile
        p.manager = None
        p.department = dept_objs["Engineering"]
        p.salary_annual = 250000
        p.employment_type = "full_time"
        p.save()
        _create_leave(u)
        
    # VPs
    for u in vps:
        p = u.profile
        p.manager = random.choice(executives)
        p.department = random.choice(list(dept_objs.values()))
        p.salary_annual = 150000
        p.employment_type = "full_time"
        p.save()
        _create_leave(u)
        
    # Managers
    for u in managers:
        p = u.profile
        p.manager = random.choice(vps)
        p.department = p.manager.profile.department
        p.salary_annual = 100000
        p.employment_type = "full_time"
        p.save()
        _create_leave(u)
        
    # Associates
    for u in associates:
        p = u.profile
        p.manager = random.choice(managers)
        p.department = p.manager.profile.department
        p.salary_annual = random.uniform(50000, 80000)
        p.employment_type = random.choice(["full_time", "contract"])
        p.save()
        _create_leave(u)
        
    print(f"✅ Successfully seeded completely realistic Company Org Chart tracking 40 employees!")

def _create_leave(user):
    LeaveBalance.objects.create(
        user=user,
        year=datetime.now().year,
        casual_leave={"total": 12, "used": 0, "balance": 12},
        sick_leave={"total": 10, "used": 0, "balance": 10},
        earned_leave={"total": 15, "used": 0, "balance": 15},
        comp_off={"total": 0, "used": 0, "balance": 0}
    )

if __name__ == "__main__":
    seed_org_chart()
