from django.http import Http404
from rest_framework.exceptions import PermissionDenied

CHA_CWH_ROLES = ["corporate_hr_admin", "corporate_wellness_head", "longevity_physician", "clinician", "super_admin"]

def _req_corp(user):
    role = getattr(user.profile, 'role', None)
    role_name = role.name if role else None
    if role_name not in CHA_CWH_ROLES:
        raise PermissionDenied("Corporate HR Admin or Wellness Head role required")
    return True

def _tier_str(raw):
    """Extract tier string from tier field which might be a dict or string."""
    if isinstance(raw, dict):
        return raw.get("tier", "FOUNDATION")
    return raw or "FOUNDATION"
