from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, Role, Company
from datetime import datetime, timezone

class LegacyUserSerializer(serializers.ModelSerializer):
    """Safe user serializer that flattens User and UserProfile into legacy format."""
    id = serializers.CharField()
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    age = serializers.IntegerField(source='profile.age')
    dob = serializers.CharField(source='profile.dob')
    gender = serializers.CharField(source='profile.gender')
    sex = serializers.CharField(source='profile.sex')
    height_cm = serializers.FloatField(source='profile.height_cm')
    weight_kg = serializers.FloatField(source='profile.weight_kg')
    ethnicity = serializers.CharField(source='profile.ethnicity')
    franchise = serializers.CharField(source='profile.franchise')
    role = serializers.SerializerMethodField()
    phone = serializers.CharField(source='profile.phone_number')
    employee_id = serializers.CharField(source='id')
    company = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    location_confirmed = serializers.SerializerMethodField()
    managed_conditions = serializers.JSONField(source='profile.managed_conditions')
    adherence_pct = serializers.FloatField(source='profile.adherence_pct')
    streak_days = serializers.IntegerField(source='profile.streak_days')
    joined_at = serializers.DateTimeField(source='date_joined')
    is_demo = serializers.BooleanField(source='profile.is_demo')

    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'age', 'dob', 'gender', 'sex', 
            'height_cm', 'weight_kg', 'ethnicity', 'franchise', 'role', 
            'phone', 'employee_id', 'company', 'address', 
            'location_confirmed', 'managed_conditions', 'adherence_pct', 
            'streak_days', 'joined_at', 'is_demo'
        ]

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_role(self, obj):
        return obj.profile.role.name if obj.profile.role else "employee"

    def get_company(self, obj):
        return obj.profile.company.name if obj.profile.company else ""

    def get_address(self, obj):
        return {} # Legacy returns empty dict

    def get_location_confirmed(self, obj):
        return False # Legacy constant

class LegacyRegisterSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    dob = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    height_cm = serializers.FloatField(required=False, default=170.0)
    weight_kg = serializers.FloatField(required=False, default=70.0)
    ethnicity = serializers.CharField(required=False, allow_blank=True)
    franchise = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, default="employee")
    phone = serializers.CharField(required=False, allow_blank=True)
    employee_id = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        name = validated_data['name']
        password = validated_data['password']
        
        # Split name for first/last
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        user = User.objects.create_user(
            username=email, # Use email as username for legacy compatibility
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Calculate age
        age = 35
        dob_str = validated_data.get('dob', '')
        if dob_str:
            try:
                from dateutil.parser import parse as parse_date
                born = parse_date(dob_str)
                today = datetime.now(timezone.utc)
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            except Exception:
                pass
        
        # Map sex code
        gender = validated_data.get('gender', '')
        sex_code = "M" if gender == "Male" else ("F" if gender == "Female" else "O")
        
        # Get role/company objects if they exist
        role_name = validated_data.get('role', 'employee')
        role_obj, _ = Role.objects.get_or_create(name=role_name)
        
        company_name = validated_data.get('company', '')
        company_obj = None
        if company_name:
            company_obj, _ = Company.objects.get_or_create(name=company_name)
            
        # Update Profile
        profile = user.profile
        profile.age = age
        profile.dob = dob_str
        profile.gender = gender
        profile.sex = sex_code
        profile.height_cm = validated_data.get('height_cm', 170.0)
        profile.weight_kg = validated_data.get('weight_kg', 70.0)
        profile.ethnicity = validated_data.get('ethnicity', '')
        profile.franchise = validated_data.get('franchise', '')
        profile.role = role_obj
        profile.company = company_obj
        profile.phone_number = validated_data.get('phone', '')
        profile.is_email_verified = True # Legacy auto-verifies
        profile.save()
        
        return user
