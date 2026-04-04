from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    LabPartner, LabPanel, LabOrder, 
    PharmacyCatalogItem, PharmacyOrder, PharmacyOrderItem
)

class LabPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPartner
        fields = '__all__'

class LabPanelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPanel
        fields = '__all__'

class LabOrderSerializer(serializers.ModelSerializer):
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    member_id = serializers.CharField(source='patient.id', read_only=True)
    panel_name = serializers.CharField(source='panel.name', read_only=True)
    panel_category = serializers.CharField(source='panel.category', read_only=True)
    biomarkers = serializers.JSONField(source='panel.biomarkers', read_only=True)
    loinc = serializers.CharField(source='panel.loinc', read_only=True)
    lab_partner_name = serializers.CharField(source='lab_partner.name', read_only=True)
    lab_accreditation = serializers.CharField(source='lab_partner.accreditation', read_only=True)
    
    specimen = serializers.SerializerMethodField()

    class Meta:
        model = LabOrder
        fields = [
            'id', 'order_number', 'member_id', 'ordered_by', 'ordered_by_name',
            'panel_id', 'panel_name', 'panel_category', 'biomarkers', 'loinc',
            'priority', 'fasting_required', 'status', 'notes', 'price',
            'turnaround_days', 'lab_partner_id', 'lab_partner_name', 'lab_accreditation',
            'specimen', 'ordered_at', 'collected_at', 'processing_at', 'resulted_at',
            'results', 'result_notes', 'abnormal_count'
        ]

    def get_specimen(self, obj):
        return {
            "type": obj.specimen_type,
            "collected": obj.specimen_collected,
            "collection_time": obj.collected_at.isoformat() if obj.collected_at else None,
            "barcode": obj.specimen_barcode,
            "temperature": "ambient", # Static in legacy
            "transport_status": obj.specimen_transport_status,
        }

class PharmacyCatalogItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyCatalogItem
        fields = '__all__'

class PharmacyOrderItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='catalog_item.name', read_only=True)
    type = serializers.CharField(source='catalog_item.type', read_only=True)
    category = serializers.CharField(source='catalog_item.category', read_only=True)
    price = serializers.DecimalField(source='price_at_order', max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyOrderItem
        fields = ['item_id', 'name', 'type', 'category', 'quantity', 'price', 'line_total', 'dosing_instructions']

    def get_line_total(self, obj):
        return round(float(obj.price_at_order) * obj.quantity, 2)

class PharmacyOrderSerializer(serializers.ModelSerializer):
    ordered_by_name = serializers.CharField(source='ordered_by.get_full_name', read_only=True)
    member_id = serializers.CharField(source='patient.id', read_only=True)
    items = PharmacyOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PharmacyOrder
        fields = [
            'id', 'order_number', 'member_id', 'ordered_by', 'ordered_by_name',
            'order_type', 'items', 'total_price', 'status', 'pharmacy_id',
            'notes', 'ordered_at', 'dispensed_at'
        ]
