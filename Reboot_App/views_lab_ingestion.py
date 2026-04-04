from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import random
import logging
from datetime import datetime

from .models import (
    LabIngestionReport, BiomarkerDefinition, BiomarkerResult, 
    Notification, CCAssignment, SampleBooking
)
from .serializers import LabIngestionReportSerializer

logger = logging.getLogger(__name__)

def _classify_value(value, defn):
    """Classify a biomarker value as optimal, monitor, or at_risk."""
    if defn.longevity_low is not None and defn.longevity_high is not None:
        if defn.longevity_low <= value <= defn.longevity_high:
            return "optimal"
    
    if defn.optimal_low is not None and defn.optimal_high is not None:
        if defn.optimal_low <= value <= defn.optimal_high:
            return "monitor"
            
    return "at_risk"

def _classify_risk_alert(value, defn):
    """Classify risk alert level: CRITICAL/HIGH/MODERATE/LOW."""
    if defn.optimal_low is None or defn.optimal_high is None:
        return "LOW"
        
    danger_low = defn.optimal_low * 0.4
    danger_high = defn.optimal_high * 2.5
    
    if value <= danger_low or value >= danger_high:
        return "CRITICAL"
    elif value < defn.optimal_low * 0.7 or value > defn.optimal_high * 1.5:
        return "HIGH"
    elif value < defn.optimal_low or value > defn.optimal_high:
        return "MODERATE"
    return "LOW"

def _validate_ocr_values(extracted):
    """Apply OCR validation rules."""
    issues = []
    for val in extracted:
        code = val["biomarker_code"]
        try:
            defn = BiomarkerDefinition.objects.get(code=code)
        except BiomarkerDefinition.DoesNotExist:
            continue
            
        # Rule 1: OCR confidence threshold
        if val.get("ocr_confidence", 1) < 0.95:
            val["needs_review"] = True
            issues.append({"rule": "confidence", "biomarker": code, "detail": f"Confidence {val['ocr_confidence']:.2f} < 0.95"})
            
        # Rule 2: Numeric range check
        if defn.optimal_low is not None and defn.optimal_high is not None:
            plausible_min = defn.optimal_low * 0.1
            plausible_max = defn.optimal_high * 5
            if val["value"] < plausible_min or val["value"] > plausible_max:
                val["needs_review"] = True
                issues.append({"rule": "range", "biomarker": code, "detail": f"Value {val['value']} outside plausible range"})
                
        # Rule 3: Unit validation
        if defn.unit and val.get("unit") != defn.unit:
            val["unit_mismatch"] = True
            issues.append({"rule": "unit", "biomarker": code, "detail": f"Expected {defn.unit}, got {val.get('unit')}"})
            
    return issues

def _simulated_ocr_extract():
    """Simulate OCR extraction from a lab PDF."""
    extracted = []
    definitions = BiomarkerDefinition.objects.filter(data_source="lab")
    # If no lab definitions, use the ones we just seeded
    if not definitions.exists():
        codes = ["fasting_glucose", "hba1c", "total_cholesterol", "ldl_cholesterol", 
                 "hdl_cholesterol", "triglycerides", "tsh", "vitamin_d", "vitamin_b12", 
                 "hscrp", "ferritin", "homocysteine", "cortisol", "creatinine"]
        definitions = BiomarkerDefinition.objects.filter(code__in=codes)

    for defn in definitions:
        if defn.optimal_low is None or defn.optimal_high is None:
            continue
            
        mid = (defn.optimal_low + defn.optimal_high) / 2
        spread = (defn.optimal_high - defn.optimal_low) * 0.6
        value = round(mid + random.uniform(-spread, spread), 2)
        confidence = round(random.uniform(0.92, 0.99), 2)
        
        extracted.append({
            "biomarker_code": defn.code,
            "name": defn.name,
            "value": value,
            "unit": defn.unit,
            "reference_low": defn.optimal_low,
            "reference_high": defn.optimal_high,
            "longevity_low": defn.longevity_low,
            "longevity_high": defn.longevity_high,
            "status": _classify_value(value, defn),
            "ocr_confidence": confidence,
            "needs_review": confidence < 0.95,
        })
    return extracted

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_report(request):
    """Upload/receive a lab report PDF and process via OCR pipeline."""
    lab_partner = request.data.get("lab_partner", "MedPlus")
    patient_id = request.data.get("patient_id")
    
    if patient_id:
        try:
            target_user = User.objects.get(id=patient_id)
        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        target_user = request.user
        
    extracted_values = _simulated_ocr_extract()
    validation_issues = _validate_ocr_values(extracted_values)
    
    # Add risk alert levels
    for val in extracted_values:
        try:
            defn = BiomarkerDefinition.objects.get(code=val["biomarker_code"])
            val["risk_alert"] = _classify_risk_alert(val["value"], defn)
        except BiomarkerDefinition.DoesNotExist:
            val["risk_alert"] = "LOW"
            
    # Duplicate check
    today = timezone.now().date()
    existing_today = LabIngestionReport.objects.filter(
        patient=target_user, 
        uploaded_at__date=today
    ).exists()
    
    if existing_today:
        validation_issues.append({"rule": "duplicate", "biomarker": "N/A", "detail": "A report was already uploaded today for this patient"})
        
    report = LabIngestionReport.objects.create(
        patient=target_user,
        lab_partner=lab_partner,
        report_type="blood_panel",
        pdf_url=f"/static/reports/report_{uuid.uuid4().hex[:8]}.pdf",
        ocr_status="completed",
        extracted_values=extracted_values,
        validation_issues=validation_issues,
        needs_review=any(v.get("needs_review", False) for v in extracted_values) or len(validation_issues) > 0,
        review_status="pending" if any(v.get("needs_review", False) for v in extracted_values) else "auto_approved",
        ingested_to_biomarkers=False
    )
    
    # Check for critical alerts and trigger notifications
    critical_markers = [v for v in extracted_values if v.get("risk_alert") == "CRITICAL"]
    if critical_markers:
        care_team = CCAssignment.objects.filter(member=target_user)
        for assignment in care_team:
            Notification.objects.create(
                user=assignment.cc,
                type="critical_biomarker_alert",
                message=f"CRITICAL: {len(critical_markers)} biomarker(s) flagged for patient {target_user.username}. Immediate review required.",
                is_read=False,
                data={"report_id": str(report.id), "patient_id": target_user.id}
            )
            
    serializer = LabIngestionReportSerializer(report)
    return Response({
        "report": serializer.data,
        "total_biomarkers": len(extracted_values),
        "needs_review": report.needs_review,
        "review_count": sum(1 for v in extracted_values if v.get("needs_review")),
        "critical_alerts": len(critical_markers),
        "validation_issues": validation_issues
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_reports(request, patient_id):
    """Get all lab reports for a patient."""
    reports = LabIngestionReport.objects.filter(patient_id=patient_id).order_by('-uploaded_at')
    serializer = LabIngestionReportSerializer(reports, many=True)
    return Response({"reports": serializer.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_report_detail(request, report_id):
    """Get detailed report with visual biomarker cards."""
    report = get_object_or_404(LabIngestionReport, id=report_id)
    
    visual_cards = []
    for val in report.extracted_values:
        explanation = ""
        if val["status"] == "optimal":
            explanation = f"Your {val['name']} is in the longevity optimal range. Keep it up!"
        elif val["status"] == "monitor":
            explanation = f"Your {val['name']} is within normal range but could be optimized for longevity."
        else:
            explanation = f"Your {val['name']} needs attention. Consult your care team for guidance."
        visual_cards.append({**val, "explanation": explanation})
        
    status_summary = {
        "optimal": sum(1 for v in visual_cards if v["status"] == "optimal"),
        "monitor": sum(1 for v in visual_cards if v["status"] == "monitor"),
        "at_risk": sum(1 for v in visual_cards if v["status"] == "at_risk"),
        "total": len(visual_cards),
    }
    
    serializer = LabIngestionReportSerializer(report)
    return Response({
        "report": serializer.data, 
        "visual_cards": visual_cards, 
        "status_summary": status_summary
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_report_values(request, report_id):
    """Approve/correct OCR-extracted values and ingest into biomarker database."""
    report = get_object_or_404(LabIngestionReport, id=report_id)
    
    corrected_values = request.data.get("corrected_values", [])
    values_to_ingest = report.extracted_values
    
    for correction in corrected_values:
        code = correction.get("biomarker_code")
        new_value = correction.get("value")
        for val in values_to_ingest:
            if val["biomarker_code"] == code:
                val["value"] = new_value
                val["needs_review"] = False
                val["manually_corrected"] = True
                try:
                    defn = BiomarkerDefinition.objects.get(code=code)
                    val["status"] = _classify_value(new_value, defn)
                except BiomarkerDefinition.DoesNotExist:
                    pass
                    
    ingested = 0
    for val in values_to_ingest:
        try:
            defn = BiomarkerDefinition.objects.get(code=val["biomarker_code"])
            BiomarkerResult.objects.create(
                user=report.patient,
                biomarker=defn,
                value=val["value"],
                source=f"LAB_OCR_{report.lab_partner}",
                collected_at=report.uploaded_at
            )
            ingested += 1
        except BiomarkerDefinition.DoesNotExist:
            logger.warning(f"Biomarker definition missing for {val['biomarker_code']}")
            
    report.review_status = "approved"
    report.ingested_to_biomarkers = True
    report.extracted_values = values_to_ingest
    report.processed_at = timezone.now()
    report.save()
    
    Notification.objects.create(
        user=report.patient,
        type="report_ready",
        message="Your health report is ready! Tap to view your results and Health Performance Score.",
        is_read=False,
        data={"report_id": str(report.id)}
    )
    
    return Response({"ingested": ingested, "report_id": str(report.id), "status": "approved"})

@api_view(['POST'])
@permission_classes([]) # Webhooks usually have different auth
def lab_partner_webhook(request):
    """Webhook endpoint for lab partner to push status updates and reports."""
    data = request.data
    event_type = data.get("event", "")
    order_id = data.get("order_id", "")
    
    if event_type in ["sample_received", "report_ready"]:
        try:
            # Note: LabOrder doesn't have lab_order_id field in models.py, 
            # it has order_number or id. SampleBooking has lab_order (FK to LabOrder).
            # The FastAPI updated db.sample_bookings with lab_order_id.
            # Here we try to find the LabOrder and then update associated bookings.
            from .models import LabOrder
            order = LabOrder.objects.filter(order_number=order_id).first()
            if order:
                status_map = {
                    "sample_received": "sample_received_at_lab",
                    "report_ready": "report_ready"
                }
                new_status = status_map.get(event_type)
                order.status = new_status
                order.save()
                
                # Update bookings linked to this order
                bookings = SampleBooking.objects.filter(lab_order=order)
                for booking in bookings:
                    booking.status = new_status
                    booking.save()
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            
    return Response({"status": "received"})
