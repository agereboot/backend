from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import NutritionLog, NutritionPlan
from .serializers import NutritionLogSerializer, NutritionPlanSerializer
from .hps_engine.employee import SAMPLE_NUTRITION_PLANS

EXTENDED_NUTRIENT_KEYS = [
    "calories", "protein", "carbs", "fats", "fiber",
    "pufa", "non_pufa", "omega3", "omega6",
    "vitamin_a", "vitamin_c", "vitamin_d", "vitamin_e", "vitamin_k",
    "vitamin_b12", "folate", "iron", "calcium", "magnesium", "zinc",
    "potassium", "sodium", "selenium", "antioxidants"
]

DEFAULT_NUTRIENT_TARGETS = {
    "calories": 2000, "protein": 120, "carbs": 220, "fats": 65, "fiber": 30,
    "pufa": 20, "non_pufa": 25, "omega3": 2.5, "omega6": 12,
    "vitamin_a": 900, "vitamin_c": 90, "vitamin_d": 20, "vitamin_e": 15, "vitamin_k": 120,
    "vitamin_b12": 2.4, "folate": 400, "iron": 18, "calcium": 1000, "magnesium": 400, "zinc": 11,
    "potassium": 2600, "sodium": 2300, "selenium": 55, "antioxidants": 10000
}

NUTRIENT_UNITS = {
    "calories": "kcal", "protein": "g", "carbs": "g", "fats": "g", "fiber": "g",
    "pufa": "g", "non_pufa": "g", "omega3": "g", "omega6": "g",
    "vitamin_a": "mcg", "vitamin_c": "mg", "vitamin_d": "mcg", "vitamin_e": "mg", "vitamin_k": "mcg",
    "vitamin_b12": "mcg", "folate": "mcg", "iron": "mg", "calcium": "mg", "magnesium": "mg", "zinc": "mg",
    "potassium": "mg", "sodium": "mg", "selenium": "mcg", "antioxidants": "ORAC"
}

NUTRIENT_GROUPS = {
    "macros": ["calories", "protein", "carbs", "fats", "fiber"],
    "fats_detail": ["pufa", "non_pufa", "omega3", "omega6"],
    "vitamins": ["vitamin_a", "vitamin_c", "vitamin_d", "vitamin_e", "vitamin_k", "vitamin_b12", "folate"],
    "minerals": ["iron", "calcium", "magnesium", "zinc", "potassium", "sodium", "selenium"],
    "antioxidants": ["antioxidants"]
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutrition_plan(request):
    try:
        saved = NutritionPlan.objects.get(user=request.user)
        if saved.plan:
            return Response({
                "plan": saved.plan, 
                "daily_target": saved.daily_target or DEFAULT_NUTRIENT_TARGETS, 
                "generated": True
            })
    except NutritionPlan.DoesNotExist:
        pass
        
    return Response({
        "plan": SAMPLE_NUTRITION_PLANS, 
        "daily_target": DEFAULT_NUTRIENT_TARGETS, 
        "generated": False
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutrition_logs(request):
    logs = NutritionLog.objects.filter(user=request.user).order_by('-logged_at')[:60]
    return Response({"logs": NutritionLogSerializer(logs, many=True).data, "count": logs.count()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_nutrition(request):
    data = request.data
    date = data.get("date") or timezone.now().strftime("%Y-%m-%d")
    
    items = data.get("items", [])
    totals = {k: 0 for k in EXTENDED_NUTRIENT_KEYS}
    
    for item in items:
        for k in totals:
            totals[k] += item.get(k, 0)
            
    foods = [it.get("name", it.get("item", "")) for it in items] if items else data.get("foods", [])
    
    from datetime import datetime
    dt = timezone.make_aware(datetime.strptime(date, "%Y-%m-%d"))
    
    log = NutritionLog.objects.create(
        user=request.user,
        date=dt.date(),
        meal_type=data.get("meal_type", "snack"),
        items=items,
        totals=totals,
        foods=foods,
        total_calories=totals.get("calories", 0)
    )
    
    # Simple credits logic
    today_count = NutritionLog.objects.filter(user=request.user, date=dt.date()).count()
    points_earned = 5 if today_count == 1 else 2
    
    # Internal credits call could be added here if needed
    
    result = NutritionLogSerializer(log).data
    result["points_earned"] = points_earned
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_nutrition_trends(request):
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    logs = list(NutritionLog.objects.filter(
        user=request.user, 
        date__gte=thirty_days_ago
    ).values())

    daily = {}
    for l in logs:
        d = l["date"].strftime("%Y-%m-%d")
        if d not in daily:
            daily[d] = {k: 0 for k in EXTENDED_NUTRIENT_KEYS}
            daily[d]["meals_count"] = 0
            
        daily[d]["meals_count"] += 1
        t = l.get("totals", {})
        for k in EXTENDED_NUTRIENT_KEYS:
            daily[d][k] += t.get(k, 0)

    try:
        custom = NutritionPlan.objects.get(user=request.user)
        targets = custom.daily_target or DEFAULT_NUTRIENT_TARGETS
    except NutritionPlan.DoesNotExist:
        targets = DEFAULT_NUTRIENT_TARGETS

    trend_data = []
    for d in sorted(daily.keys()):
        entry = {"date": d, "meals_count": daily[d]["meals_count"]}
        for k in EXTENDED_NUTRIENT_KEYS:
            entry[k] = round(daily[d][k], 1)
        trend_data.append(entry)

    # Simplified weekly calculation could be added here
    # ...
    
    return Response({
        "daily": trend_data, 
        "weekly_averages": {}, 
        "targets": targets,
        "nutrient_groups": NUTRIENT_GROUPS, 
        "nutrient_units": NUTRIENT_UNITS,
        "days_tracked": len(trend_data)
    })

# Note: The LLM meal analysis / generation endpoints 
# from the Flask app are omitted or can be re-added later, 
# as they require the `emergentintegrations` package.
