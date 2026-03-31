from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid
import re
import random

# Import models
from .models import (
    BiomarkerDefinition, BiomarkerResult, ManualEntry,
    WearableDevice, WearableConnection, ReportRepository, CognitiveAssessmentResult,
    PillarConfig
)
from .serializers import (
    BiomarkerDefinitionSerializer, BiomarkerResultSerializer,
    BulkBiomarkerIngestSerializer, ManualEntrySerializer,
    WearableConnectionSerializer, ReportRepositorySerializer
)
from .hps_engine.normative import BIOMARKER_DEFINITIONS
from .hps_engine.scoring import compute_hps


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ingest_biomarkers(request):
    serializer = BulkBiomarkerIngestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    results = []
    for bm in serializer.validated_data['biomarkers']:
        code = bm['biomarker_code']
        if code not in BIOMARKER_DEFINITIONS:
            continue
            
        # Get or create BiomarkerDefinition so foreign key constraints don't fail
        defn_data = BIOMARKER_DEFINITIONS[code]
        defn, _ = BiomarkerDefinition.objects.get_or_create(
            code=code,
            defaults={
                'name': defn_data['name'],
                'domain': defn_data['domain'],
                'pillar': defn_data['pillar'],
                'unit': defn_data['unit'],
                'direction': defn_data.get('direction', 'optimal_range'),
                'optimal_low': defn_data.get('optimal_low'),
                'optimal_high': defn_data.get('optimal_high')
            }
        )
        
        result = BiomarkerResult.objects.create(
            user=request.user,
            biomarker=defn,
            value=bm['value'],
            source=bm.get('source', 'MANUAL'),
            collected_at=bm.get('collected_at') or timezone.now()
        )
        results.append(BiomarkerResultSerializer(result).data)
        
    return Response({"ingested": len(results), "results": results})


@api_view(['GET'])
def get_biomarker_definitions(request):
    defs = []
    for code, defn in BIOMARKER_DEFINITIONS.items():
        defs.append({
            "code": code,
            "name": defn["name"],
            "domain": defn["domain"],
            "pillar": defn["pillar"],
            "unit": defn["unit"],
            "direction": defn["direction"],
            "optimal_low": defn.get("optimal_low"),
            "optimal_high": defn.get("optimal_high"),
        })
    return Response({"definitions": defs})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pillar_dashboard(request):
    from .hps_engine.normative import PILLAR_CONFIG
    
    # Django Query
    all_bms = BiomarkerResult.objects.filter(user=request.user).order_by('-collected_at')[:500]
    
    latest_by_code = {}
    history_by_code = {}
    
    for bm in all_bms:
        code = bm.biomarker_id
        if code not in latest_by_code:
            latest_by_code[code] = bm
        if code not in history_by_code:
            history_by_code[code] = []
        if len(history_by_code[code]) < 10:
            history_by_code[code].append(bm)
            
    pillars = {}
    for code, defn in BIOMARKER_DEFINITIONS.items():
        pillar = defn["pillar"]
        if pillar not in pillars:
            cfg = PILLAR_CONFIG.get(pillar, {})
            pillars[pillar] = {
                "code": pillar, "name": cfg.get("name", pillar), 
                "color": cfg.get("color", "#7B35D8"), 
                "biomarkers": [], "red": 0, "yellow": 0, "green": 0
            }
            
        bm = latest_by_code.get(code)
        if bm:
            val = bm.value
            opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
            direction = defn.get("direction", "optimal_range")
            if direction == "lower_better":
                status = "green" if val <= opt_high else ("yellow" if val <= opt_high * 1.3 else "red")
            elif direction == "higher_better":
                status = "green" if val >= opt_low else ("yellow" if val >= opt_low * 0.7 else "red")
            else:
                status = "green" if opt_low <= val <= opt_high else ("yellow" if opt_low * 0.8 <= val <= opt_high * 1.2 else "red")
            
            history = [{"value": round(h.value, 2), "date": h.collected_at.strftime('%Y-%m-%d')} for h in reversed(history_by_code.get(code, []))]
            pillars[pillar]["biomarkers"].append({
                "code": code, "name": defn["name"], "value": round(val, 2), "unit": defn["unit"], 
                "domain": defn["domain"], "optimal_low": opt_low, "optimal_high": opt_high, 
                "direction": direction, "status": status, "history": history, "data_source": defn.get("data_source", "manual")
            })
            pillars[pillar][status] += 1
        else:
            pillars[pillar]["biomarkers"].append({
                "code": code, "name": defn["name"], "value": None, "unit": defn["unit"], 
                "domain": defn["domain"], "optimal_low": defn.get("optimal_low"), "optimal_high": defn.get("optimal_high"), 
                "direction": defn.get("direction"), "status": "missing", "history": [], "data_source": defn.get("data_source", "manual")
            })
            
    return Response({"pillars": pillars})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_manual_entry(request):
    code = request.data.get("biomarker_code")
    val = request.data.get("value")
    notes = request.data.get("notes", "")
    
    defn = BIOMARKER_DEFINITIONS.get(code)
    if not defn:
        return Response({"error": "Unknown biomarker code"}, status=status.HTTP_400_BAD_REQUEST)
        
    opt_low, opt_high = defn.get("optimal_low", 0), defn.get("optimal_high", 100)
    system_flag = "normal" if opt_low * 0.3 <= float(val) <= opt_high * 3 else "flagged_out_of_range"
    
    # Get or create BiomarkerDefinition
    bdef, _ = BiomarkerDefinition.objects.get_or_create(code=code, defaults={'name': defn['name'], 'pillar': defn['pillar']})
    
    entry = ManualEntry.objects.create(
        user=request.user,
        biomarker=bdef,
        value=val,
        notes=notes,
        entered_by=request.user.first_name,
        entered_by_role="employee",
        system_validation=system_flag,
        clinician_validation="pending",
        status="pending_validation"
    )
    
    return Response(ManualEntrySerializer(entry).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manual_entries(request):
    entries = ManualEntry.objects.filter(user=request.user).order_by('-created_at')[:50]
    return Response({"entries": ManualEntrySerializer(entries, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_biomarkers(request, user_id):
    results = BiomarkerResult.objects.filter(user__id=user_id).order_by('-ingested_at')[:500]
    return Response({"biomarkers": BiomarkerResultSerializer(results, many=True).data, "count": results.count()})


# Wearable
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_connections(request):
    connections = WearableConnection.objects.filter(user=request.user)
    return Response({"connections": WearableConnectionSerializer(connections, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_lab_results(request):
    from .serializers import LabUploadSerializer
    serializer = LabUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    lab_name = serializer.validated_data['lab_name']
    results = serializer.validated_data['results']
    
    biomarkers = []
    for code, value in results.items():
        if code in BIOMARKER_DEFINITIONS:
            biomarkers.append({
                "biomarker_code": code,
                "value": value,
                "source": f"LAB_{lab_name.upper().replace(' ', '_')}"
            })
            
    if not biomarkers:
        return Response({"error": "No valid biomarkers in lab results"}, status=400)
        
    # We call internal logic without HTTP wrapper
    request.data['biomarkers'] = biomarkers
    return ingest_biomarkers(request)

