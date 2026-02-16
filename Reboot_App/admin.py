# from django.contrib import admin
# from .models import UserProfile,Question, QuestionOption, UserAnswer

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "username",
#         "email",
#         "is_google_user",
#     )

#     search_fields = (
#         "user__username",
#         "user__email",
#     )

#     list_filter = (
#         "is_google_user",
#     )

#     def username(self, obj):
#         return obj.user.username

#     def email(self, obj):
#         return obj.user.email



# class QuestionOptionInline(admin.TabularInline):
#     model = QuestionOption
#     extra = 1
    
# @admin.register(Question)
# class QuestionAdmin(admin.ModelAdmin):
#     list_display = ("id", "text", "question_type", "order", "is_required")
#     list_filter = ("question_type",)
#     ordering = ("order", "id")
#     inlines = [QuestionOptionInline]


# @admin.register(UserAnswer)
# class UserAnswerAdmin(admin.ModelAdmin):
#     list_display = (
#         "user",
#         "question",
#         "selected_option",
#         "answer_number",
#         "answer_date",
#         "created_at",
#     )
#     list_filter = ("question__question_type",)
#     readonly_fields = ("created_at",)


from django.contrib import admin
from .models import (
    Role,
    Company,
    Location,
    Department,
    Plan,
    UserProfile,
    EmployeePlan,
    Question,
    QuestionOption,
    UserAnswer,
)

from django.db import models


def get_all_fields(model):
    return [field.name for field in model._meta.fields]


def get_searchable_fields(model):
    searchable_types = (
        models.CharField,
        models.TextField,
        models.EmailField,
        models.SlugField,
    )

    return [
        field.name
        for field in model._meta.fields
        if isinstance(field, searchable_types)
    ]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Role)
    search_fields = get_searchable_fields(Role)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Company)
    search_fields = get_searchable_fields(Company)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Location)
    search_fields = get_searchable_fields(Location)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Department)
    search_fields = get_searchable_fields(Department)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = get_all_fields(Plan)
    search_fields = get_searchable_fields(Plan)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = get_all_fields(UserProfile)
    search_fields = get_searchable_fields(UserProfile) + [
        "user__username",
        "user__email",
    ]


@admin.register(EmployeePlan)
class EmployeePlanAdmin(admin.ModelAdmin):
    list_display = get_all_fields(EmployeePlan)
    search_fields = ("user__username", "plan__name")

