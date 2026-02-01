from django.contrib import admin
from .models import UserProfile,Question, QuestionOption, UserAnswer

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "is_google_user",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    list_filter = (
        "is_google_user",
    )

    def username(self, obj):
        return obj.user.username

    def email(self, obj):
        return obj.user.email



class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1
    
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question_type", "order", "is_required")
    list_filter = ("question_type",)
    ordering = ("order", "id")
    inlines = [QuestionOptionInline]


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "question",
        "selected_option",
        "answer_number",
        "answer_date",
        "created_at",
    )
    list_filter = ("question__question_type",)
    readonly_fields = ("created_at",)
