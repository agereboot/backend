import os
import django
import random
from datetime import datetime, timezone, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Reboot.settings")
django.setup()

from Reboot_App.models import Asset
from django.contrib.auth.models import User

ASSET_TYPES = ["laptop", "monitor", "keyboard", "headset", "phone", "desk", "chair"]
LAPTOP_BRANDS = ["Apple", "Dell", "Lenovo", "HP"]
MONITOR_BRANDS = ["LG", "Dell", "Samsung"]
STATUSES = ["available", "assigned", "under_repair"]

def seed_assets():
    print("🧹 Wiping previous old assets...")
    Asset.objects.all().delete()
    
    users = list(User.objects.all())
    if not users:
        print("❌ No users found to assign assets to. Aborting.")
        return
        
    print("💻 Generating pristine 60+ IT Hardware Assets...")
    assets_to_create = []
    
    for i in range(1, 61):
        atype = random.choices(ASSET_TYPES, weights=[40, 20, 10, 10, 10, 5, 5])[0]
        brand = random.choice(LAPTOP_BRANDS) if atype == "laptop" else (random.choice(MONITOR_BRANDS) if atype == "monitor" else "Generic")
        model = f"Pro Series {random.randint(2020, 2026)}"
        status = random.choice(STATUSES)
        
        assigned_user = random.choice(users) if status == "assigned" else None
        
        ast = Asset(
            asset_tag=f"AST-{i:04d}",
            asset_type=atype,
            brand=brand,
            model=model,
            serial_number=f"SN-{random.randint(1000000, 9999999)}",
            purchase_date=(datetime.now() - timedelta(days=random.randint(30, 1000))).strftime("%Y-%m-%d"),
            purchase_cost=random.uniform(500, 2500) if atype == "laptop" else random.uniform(50, 400),
            warranty_expiry=(datetime.now() + timedelta(days=random.randint(100, 800))).strftime("%Y-%m-%d"),
            status=status,
            assigned_to=assigned_user,
            assigned_to_name=f"{assigned_user.first_name} {assigned_user.last_name}".strip() or assigned_user.username if assigned_user else None,
            assigned_at=timezone.now() if assigned_user else None,
            history=[{"action": "purchased", "date": datetime.now().strftime("%Y-%m-%d")}]
        )
        
        if assigned_user:
            ast.history.append({"action": "assigned", "to": str(assigned_user.id), "at": timezone.now().isoformat()})
            
        assets_to_create.append(ast)
        
    Asset.objects.bulk_create(assets_to_create)
    print("✅ Dummy HRMS Asset Hardware correctly natively seeded into Postgres/SQLite Dashboard!")

if __name__ == "__main__":
    seed_assets()
