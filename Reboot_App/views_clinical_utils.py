from django.core.exceptions import PermissionDenied

def _req_hcp(user):
    """Enforce HCP role check."""
    # Clinical roles as defined in Flask project
    ALL_HCP = {
        "longevity_physician", "fitness_coach", "psychologist",
        "physical_therapist", "nutritional_coach", "nurse_navigator",
        "corporate_hr_admin", "corporate_wellness_head"
    }
    # Check if role belongs to either profile or legacy alias
    role = getattr(user.profile.role, 'name', '')
    
    # Aliases
    LEGACY_ALIASES = {
        "clinician": "longevity_physician", 
        "coach": "fitness_coach",
        "medical_director": "longevity_physician", 
        "clinical_admin": "nurse_navigator"
    }
    
    if role in ALL_HCP or role in LEGACY_ALIASES:
        return True
    raise PermissionDenied("Access restricted to healthcare professionals")

def _req_prescriber(user):
    """Enforce prescribing authority check."""
    PRESCRIBING_ROLES = {"longevity_physician", "clinician", "medical_director"}
    role = getattr(user.profile.role, 'name', '')
    
    if role in PRESCRIBING_ROLES:
        return True
    raise PermissionDenied("Prescribing authority required (Longevity Physician)")
