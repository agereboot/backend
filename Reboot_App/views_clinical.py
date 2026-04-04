from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime
import uuid
import random
from django.db import transaction
from django.contrib.auth.models import User
from .models import (
    LabPartner, LabPanel, LabOrder, 
    PharmacyCatalogItem, PharmacyOrder, PharmacyOrderItem,
    Notification, BiomarkerResult
)
from .serializers_clinical import (
    LabPartnerSerializer, LabPanelSerializer, LabOrderSerializer,
    PharmacyCatalogItemSerializer, PharmacyOrderSerializer
)
from .views_clinical_utils import _req_hcp, _req_prescriber

# ─── LAB ENDPOINTS ──────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_lab_partners(request):
    _req_hcp(request.user)
    partners = LabPartner.objects.all()
    serializer = LabPartnerSerializer(partners, many=True)
    return Response({"partners": serializer.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_lab_panels(request):
    _req_hcp(request.user)
    panels = LabPanel.objects.all()
    serializer = LabPanelSerializer(panels, many=True)
    return Response({"panels": serializer.data, "total": len(serializer.data)})

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lab_orders_view(request):
    _req_hcp(request.user)
    
    if request.method == 'GET':
        member_id = request.query_params.get("member_id", "")
        status = request.query_params.get("status", "")
        query = {}
        if member_id: query["patient_id"] = member_id
        if status: query["status"] = status
        
        orders = LabOrder.objects.filter(**query).order_by("-ordered_at")[:200]
        serializer = LabOrderSerializer(orders, many=True)
        return Response({"orders": serializer.data, "total": len(serializer.data)})
        
    elif request.method == 'POST':
        _req_prescriber(request.user)
        data = request.data
        try:
            panel = LabPanel.objects.get(panel_id=data.get("panel_id"))
            patient = User.objects.get(id=data.get("member_id"))
        except (LabPanel.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Invalid panel or member ID"}, status=404)
            
        lab_partner_id = data.get("lab_partner_id") or "LP-ING"
        try:
            partner = LabPartner.objects.get(id=lab_partner_id)
        except LabPartner.DoesNotExist:
            partner = LabPartner.objects.last()
            
        order_num = f"LO-{datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
        
        order = LabOrder.objects.create(
            order_number=order_num,
            patient=patient,
            ordered_by=request.user,
            panel=panel,
            lab_partner=partner,
            priority=data.get("priority", "routine"),
            fasting_required=data.get("fasting_required", False),
            notes=data.get("notes", ""),
            price=panel.price,
            turnaround_days=panel.turnaround_days + partner.tat_modifier,
            specimen_barcode=f"SP-{str(uuid.uuid4())[:8].upper()}"
        )
        
        # Notify Patient
        Notification.objects.create(
            user=patient,
            type="lab",
            message=f"A {panel.name} has been ordered for you by {request.user.get_full_name() or 'your physician'}. Lab partner: {partner.name}.",
            data={
                "title": "Lab Order Created",
                "category": "lab",
                "source": "clinical",
                "action_url": "/biomarkers"
            }
        )
        
        serializer = LabOrderSerializer(order)
        return Response(serializer.data, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lab_order_detail(request, order_id):
    _req_hcp(request.user)
    try:
        order = LabOrder.objects.get(id=order_id)
    except LabOrder.DoesNotExist:
        return Response({"error": "Lab order not found"}, status=404)
    serializer = LabOrderSerializer(order)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_lab_order_status(request, order_id):
    _req_hcp(request.user)
    status = request.data.get("status", "collected")
    valid = ["ordered", "collected", "processing", "resulted", "cancelled"]
    if status not in valid:
        return Response({"error": f"Status must be one of: {valid}"}, status=400)
        
    try:
        order = LabOrder.objects.get(id=order_id)
    except LabOrder.DoesNotExist:
        return Response({"error": "Lab order not found"}, status=404)
        
    now = timezone.now()
    order.status = status
    if status == "collected":
        order.collected_at = now
        order.specimen_collected = True
        order.specimen_transport_status = "in_transit"
    elif status == "processing":
        order.processing_at = now
        order.specimen_transport_status = "received"
    elif status == "resulted":
        order.resulted_at = now
        order.specimen_transport_status = "completed"
        
    order.save()
    serializer = LabOrderSerializer(order)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_results(request, order_id):
    _req_hcp(request.user)
    try:
        order = LabOrder.objects.get(id=order_id)
    except LabOrder.DoesNotExist:
        return Response({"error": "Lab order not found"}, status=404)
        
    data = request.data
    results = data.get("results", [])
    processed_results = []
    abnormal_count = 0
    now = timezone.now()
    
    with transaction.atomic():
        for r in results:
            val = r.get("value", 0)
            ref_low = r.get("reference_low")
            ref_high = r.get("reference_high")
            flag = "normal"
            if ref_high is not None and val > ref_high:
                flag = "high"
                abnormal_count += 1
            elif ref_low is not None and val < ref_low:
                flag = "low"
                abnormal_count += 1
                
            res_item = {**r, "flag": flag}
            processed_results.append(res_item)
            
            # Create BiomarkerResult record
            BiomarkerResult.objects.create(
                user=order.patient,
                # In DRF, we use biomarker ForeignKey. 
                # This assumes biomarker_code is a valid BiomarkerDefinition code.
                # If not found, we might need a fallback or stricter validation.
                biomarker_id=r.get("test_name"), # Simulating lookup
                value=val,
                source="lab_order",
                collected_at=order.collected_at or now,
                data={
                    "lab_order_id": str(order.id),
                    "lab_partner": order.lab_partner.name,
                    "flag": flag,
                    "unit": r.get("unit", ""),
                    "reference_low": ref_low,
                    "reference_high": ref_high
                }
            )
            
        order.results = processed_results
        order.status = "resulted"
        order.resulted_at = now
        order.result_notes = data.get("notes", "")
        order.abnormal_count = abnormal_count
        order.save()
        
    # Notify Patient
    Notification.objects.create(
        user=order.patient,
        type="lab",
        message=f"Your {order.panel.name} results are ready. {abnormal_count} abnormal finding(s)." if abnormal_count else f"Your {order.panel.name} results are ready. All within normal range!",
        data={
            "title": "Lab Results Ready",
            "category": "lab",
            "source": "clinical",
            "action_url": "/biomarkers",
            "order_id": str(order.id),
            "abnormal_count": abnormal_count
        }
    )
    
    serializer = LabOrderSerializer(order)
    return Response(serializer.data)

# ─── PHARMACY ENDPOINTS ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pharmacy_catalog(request):
    _req_hcp(request.user)
    item_type = request.query_params.get("item_type", "")
    category = request.query_params.get("category", "")
    
    query = {}
    if item_type: query["type"] = item_type
    if category: query["category"] = category
    
    items = PharmacyCatalogItem.objects.filter(**query)
    categories = sorted(list(PharmacyCatalogItem.objects.values_list("category", flat=True).distinct()))
    
    serializer = PharmacyCatalogItemSerializer(items, many=True)
    return Response({
        "items": serializer.data, 
        "categories": categories, 
        "total": len(serializer.data)
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def pharmacy_orders_view(request):
    _req_hcp(request.user)
    
    if request.method == 'GET':
        member_id = request.query_params.get("member_id", "")
        status = request.query_params.get("status", "")
        query = {}
        if member_id: query["patient_id"] = member_id
        if status: query["status"] = status
        
        orders = PharmacyOrder.objects.filter(**query).order_by("-ordered_at")[:200]
        serializer = PharmacyOrderSerializer(orders, many=True)
        return Response({"orders": serializer.data, "total": len(serializer.data)})
        
    elif request.method == 'POST':
        data = request.data
        try:
            patient = User.objects.get(id=data.get("member_id"))
        except User.DoesNotExist:
            return Response({"error": "Member not found"}, status=404)
            
        items_data = data.get("items", [])
        total_price = 0
        order_items = []
        
        with transaction.atomic():
            order_num = f"PO-{datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            order = PharmacyOrder.objects.create(
                order_number=order_num,
                patient=patient,
                ordered_by=request.user,
                order_type=data.get("order_type", "standard"),
                total_price=0, # Update later
                status="pending",
                pharmacy_id=data.get("pharmacy_id", ""),
                notes=data.get("notes", "")
            )
            
            for item_entry in items_data:
                try:
                    catalog_item = PharmacyCatalogItem.objects.get(item_id=item_entry.get("item_id"))
                except PharmacyCatalogItem.DoesNotExist:
                    continue
                    
                if catalog_item.requires_rx:
                    # Verify prescribing authority (optional check depending on user role logic)
                    try: _req_prescriber(request.user)
                    except: return Response({"error": f"Prescribing authority required for {catalog_item.name}"}, status=403)
                    
                qty = item_entry.get("quantity", 1)
                price = catalog_item.price
                line_total = price * qty
                total_price += line_total
                
                PharmacyOrderItem.objects.create(
                    order=order,
                    catalog_item=catalog_item,
                    quantity=qty,
                    price_at_order=price,
                    dosing_instructions=item_entry.get("dosing_instructions", "")
                )
                
            order.total_price = total_price
            order.save()
            
        serializer = PharmacyOrderSerializer(order)
        return Response(serializer.data, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pharmacy_order_detail(request, order_id):
    _req_hcp(request.user)
    try:
        order = PharmacyOrder.objects.get(id=order_id)
    except PharmacyOrder.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)
    serializer = PharmacyOrderSerializer(order)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_pharmacy_order_status(request, order_id):
    _req_hcp(request.user)
    status = request.data.get("status", "dispensed")
    valid = ["pending", "approved", "dispensing", "dispensed", "shipped", "delivered", "cancelled"]
    if status not in valid:
        return Response({"error": f"Status must be one of: {valid}"}, status=400)
        
    try:
        order = PharmacyOrder.objects.get(id=order_id)
    except PharmacyOrder.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)
        
    order.status = status
    if status == "dispensed":
        order.dispensed_at = timezone.now()
    order.save()
    serializer = PharmacyOrderSerializer(order)
    return Response(serializer.data)
