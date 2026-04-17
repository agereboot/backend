import os
import django
import random
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Reboot.settings')
django.setup()

from django.contrib.auth.models import User
from Reboot_App.models import PharmacyCatalogItem, PharmacyOrder, PharmacyOrderItem

PHARMACY_CATALOG = [
    {"item_id": "RX-001", "name": "Metformin 500mg", "type": "prescription", "category": "Metabolic", "requires_rx": True, "price": 12.00},
    {"item_id": "RX-002", "name": "Testosterone Cypionate 200mg/mL", "type": "prescription", "category": "Hormonal", "requires_rx": True, "price": 85.00},
    {"item_id": "RX-003", "name": "Levothyroxine 50mcg", "type": "prescription", "category": "Thyroid", "requires_rx": True, "price": 15.00},
    {"item_id": "RX-004", "name": "Low-Dose Naltrexone 4.5mg", "type": "prescription", "category": "Immune", "requires_rx": True, "price": 45.00},
    {"item_id": "RX-005", "name": "Rapamycin 1mg (Sirolimus)", "type": "prescription", "category": "Longevity", "requires_rx": True, "price": 120.00},
    {"item_id": "NT-001", "name": "NMN 500mg (Nicotinamide Mononucleotide)", "type": "nutraceutical", "category": "NAD+ Support", "requires_rx": False, "price": 65.00},
    {"item_id": "NT-002", "name": "Omega-3 Fish Oil (EPA 1000mg + DHA 500mg)", "type": "nutraceutical", "category": "Cardiovascular", "requires_rx": False, "price": 35.00},
    {"item_id": "NT-003", "name": "Vitamin D3 5000 IU + K2 MK-7 200mcg", "type": "nutraceutical", "category": "Bone & Immune", "requires_rx": False, "price": 22.00},
    {"item_id": "NT-004", "name": "Magnesium Glycinate 400mg", "type": "nutraceutical", "category": "Sleep & Recovery", "requires_rx": False, "price": 18.00},
    {"item_id": "NT-005", "name": "CoQ10 (Ubiquinol) 200mg", "type": "nutraceutical", "category": "Mitochondrial", "requires_rx": False, "price": 42.00},
    {"item_id": "NT-006", "name": "Resveratrol 500mg + Quercetin 500mg", "type": "nutraceutical", "category": "Senolytic", "requires_rx": False, "price": 55.00},
    {"item_id": "NT-007", "name": "Creatine Monohydrate 5g", "type": "nutraceutical", "category": "Muscle & Brain", "requires_rx": False, "price": 15.00},
    {"item_id": "NT-008", "name": "Ashwagandha KSM-66 600mg", "type": "nutraceutical", "category": "Adaptogen", "requires_rx": False, "price": 25.00},
    {"item_id": "NT-009", "name": "Spermidine 1mg", "type": "nutraceutical", "category": "Autophagy", "requires_rx": False, "price": 48.00},
    {"item_id": "NT-010", "name": "Alpha-Ketoglutarate (AKG) 1000mg", "type": "nutraceutical", "category": "Longevity", "requires_rx": False, "price": 38.00},
    {"item_id": "NT-011", "name": "Berberine 500mg", "type": "nutraceutical", "category": "Metabolic", "requires_rx": False, "price": 28.00},
    {"item_id": "NT-012", "name": "Probiotic Multi-Strain 50B CFU", "type": "nutraceutical", "category": "Gut Health", "requires_rx": False, "price": 32.00},
]

def seed():
    print("Starting Pharmacy data seeding...")
    
    # 1. Pharmacy Catalog
    for item in PHARMACY_CATALOG:
        PharmacyCatalogItem.objects.get_or_create(
            item_id=item["item_id"],
            defaults={
                "name": item["name"],
                "type": item["type"],
                "category": item["category"],
                "requires_rx": item["requires_rx"],
                "price": item["price"]
            }
        )
    print(f"  Seeded {len(PHARMACY_CATALOG)} catalog items.")

    # 2. Pharmacy Orders for member_04 and member_05
    clinician = User.objects.filter(email='clinical_admin@agereboot.com').first()
    targets = User.objects.filter(username__in=['member_04', 'member_05'])
    
    if not clinician or not targets.exists():
        print("Error: Required users not found. Skipping orders.")
        return

    items = list(PharmacyCatalogItem.objects.all())
    
    for member in targets:
        for i in range(2):
            status = random.choice(["pending", "approved", "dispensing", "dispensed", "shipped"])
            days_ago = random.randint(1, 45)
            ordered_at = timezone.now() - timedelta(days=days_ago)
            order_num = f"PO-{ordered_at.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            
            order = PharmacyOrder.objects.create(
                order_number=order_num,
                patient=member,
                ordered_by=clinician,
                order_type="longevity_stack" if i == 0 else "standard",
                status=status,
                ordered_at=ordered_at,
                notes=f"Clinical test order {i+1} for {member.username}",
                total_price=0 # Will update
            )
            
            # Add 2-3 items to each order
            total_price = 0
            for _ in range(random.randint(2, 3)):
                catalog_item = random.choice(items)
                qty = random.randint(1, 3)
                price = catalog_item.price
                total_price += (price * qty)
                
                PharmacyOrderItem.objects.create(
                    order=order,
                    catalog_item=catalog_item,
                    quantity=qty,
                    price_at_order=price,
                    dosing_instructions="Take 1 tablet daily with food."
                )
            
            order.total_price = total_price
            order.save()
            print(f"  Created PharmacyOrder {order_num} for {member.username} (Price: {total_price}, Status: {status})")

    print("\nPharmacy data seeding complete.")

if __name__ == "__main__":
    seed()
