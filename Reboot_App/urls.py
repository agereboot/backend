from django.urls import path
from . import views

urlpatterns = [
     path("register/", views.register_view, name="register"),
      path("verify-email/",  views.verify_email_otp),
    path("resend-otp/",  views.resend_email_otp),
         path("login/", views.login_view, name="login"),
        path("accounts/google/login/callback/", views.google_callback),
        path("phone/send-otp/", views.send_phone_otp),
    path("phone/verify-otp/", views.verify_phone_otp),
    path("phone/resend-otp/", views.resend_phone_otp),
    path("questions/", views.get_questions),
    path("answers/", views.submit_answers),
    path("answers/me/", views.get_user_answers),
    path("bulk-upload/", views.bulk_employee_upload),
    path("download-template/", views.download_employee_template),
    path("invite-employee/", views.invite_employee),
    path("reset-password/", views.reset_password),
    path("forgot-password/", views.forgot_password),
    path("employee_data/", views.employees_list_api),
    path("employees/<int:user_id>/", views.employee_edit_api, name="employee-edit"),
    path("dropdowns/locations/", views.location_dropdown_api),
    path("dropdowns/departments/", views.department_dropdown_api),
    path("dropdowns/status/", views.status_dropdown_api),
      path("hr/challenges/", views.create_challenge),
    path("hr/challenges/list/", views.hr_challenges_list),
    path("hr/challenges/<int:id>/participants/", views.challenge_participants), # challenge_id
    path("employee/challenges/", views.employee_challenges),
    path("employee/challenges/<int:id>/join/", views.join_challenge),#challenge_id
    path("employee/challenges/<int:id>/progress/", views.update_progress), #challenge_id

    # ── Role ──
    path("roles/",              views.RoleListCreateView.as_view(),    name="admin-role-list"),
    path("roles/<int:pk>/",     views.RoleDetailView.as_view(),        name="admin-role-detail"),

    # ── Company ─
    path("companies/",          views.CompanyListCreateView.as_view(), name="admin-company-list"),
    path("companies/<int:pk>/", views.CompanyDetailView.as_view(),     name="admin-company-detail"),

    # ── Location ─
    path("locations/",          views.LocationListCreateView.as_view(),  name="admin-location-list"),
    path("locations/<int:pk>/", views.LocationDetailView.as_view(),      name="admin-location-detail"),

    # ── Department ─
    path("departments/",          views.DepartmentListCreateView.as_view(),  name="admin-department-list"),
    path("departments/<int:pk>/", views.DepartmentDetailView.as_view(),      name="admin-department-detail"),

    # ── Plan ──
    path("plans/",          views.PlanListCreateView.as_view(),  name="admin-plan-list"),
    path("plans/<int:pk>/", views.PlanDetailView.as_view(),      name="admin-plan-detail"),

    # ── UserProfile ──
    path("user-profiles/",          views.UserProfileListView.as_view(),   name="admin-userprofile-list"),
    path("user-profiles/<int:pk>/", views.UserProfileDetailView.as_view(), name="admin-userprofile-detail"),

    # ── Question ──
    path("questions/",          views.QuestionListCreateView.as_view(),  name="admin-question-list"),
    path("questions/<int:pk>/", views.QuestionDetailView.as_view(),      name="admin-question-detail"),

    # ── QuestionOption ──
    path("question-options/",          views.QuestionOptionListCreateView.as_view(),  name="admin-option-list"),
    path("question-options/<int:pk>/", views.QuestionOptionDetailView.as_view(),      name="admin-option-detail"),
   


]
