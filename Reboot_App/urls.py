from django.urls import path
from . import (
    views, 
    views_biomarkers, views_hps, views_health, views_nutrition,
    views_emr, views_cc, views_telehealth, views_coach, views_ai,
    views_admin, views_corp, views_clinical
)
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
   
    path('credits/', views.get_credits, name='get_credits'),
    path('credits/purchase', views.purchase_credits_mock, name='purchase_credits'),

    # ── Biomarkers ──────────────────────────────────────────────────────────
    path("biomarkers/ingest",                   views_biomarkers.ingest_biomarkers),
    path("biomarkers/definitions/all",          views_biomarkers.get_biomarker_definitions),
    path("biomarkers/pillar-dashboard",         views_biomarkers.get_pillar_dashboard),
    path("biomarkers/manual-entry",             views_biomarkers.create_manual_entry),
    path("biomarkers/manual-entries",           views_biomarkers.get_manual_entries),
    path("biomarkers/<str:user_id>",            views_biomarkers.get_user_biomarkers),
    path("wearable/connections",                views_biomarkers.get_connections),
    path("lab/upload",                          views_biomarkers.upload_lab_results),

    # ── HPS ─────────────────────────────────────────────────────────────────
    path("hps/compute",                         views_hps.compute_hps_score),
    path("hps/score/<str:user_id>",             views_hps.get_hps_score),
    path("hps/history/<str:user_id>",           views_hps.get_hps_history),
    path("hps/predict/<str:user_id>",           views_hps.predict_hps),
    path("hps/trend",                           views_hps.get_hps_trend),

    # ── Health ──────────────────────────────────────────────────────────────
    path("health/organ-ages",                   views_health.predict_organ_ages),
    path("health/records",                      views_health.get_health_records),
    path("health/overview",                     views_health.get_health_overview),
    path("health/appointments/book",            views_health.book_appointment),

    # ── Nutrition ───────────────────────────────────────────────────────────
    path("nutrition/plan",                      views_nutrition.get_nutrition_plan),
    path("nutrition/log",                       views_nutrition.log_nutrition),
    path("nutrition/logs",                      views_nutrition.get_nutrition_logs),
    path("nutrition/trends",                    views_nutrition.get_nutrition_trends),

    # ── EMR ─────────────────────────────────────────────────────────────────
    path("emr/history",                         views_emr.get_medical_history),
    path("emr/history/update",                  views_emr.update_medical_history),
    path("emr/encounter",                       views_emr.create_emr_encounter),
    path("emr/encounter/<str:member_id>",       views_emr.get_member_encounters),
    path("emr/appointments/member",             views_emr.get_user_appointments),
    path("emr/appointments/hcp",                views_emr.get_hcp_appointments),
    path("emr/appointments/<str:pt_id>/status", views_emr.update_appointment_status),

    # ── Care Coordination (CC) ──────────────────────────────────────────────
    path("cc/roster",                           views_cc.get_cc_roster),
    path("cc/assign",                           views_cc.assign_member_to_cc),
    path("cc/alerts",                           views_cc.get_cc_alerts),
    path("cc/alerts/trigger",                   views_cc.trigger_cc_alert),
    path("cc/alerts/<str:alert_id>/resolve",    views_cc.resolve_cc_alert),
    path("cc/protocols",                        views_cc.get_cc_protocols),
    path("cc/protocols/create",                 views_cc.create_cc_protocol),
    path("cc/sessions/member/<str:member_id>",  views_cc.get_member_cc_sessions),
    path("cc/sessions/log",                     views_cc.log_cc_session),

    # ── Coach ───────────────────────────────────────────────────────────────
    path("coach/assignments",                   views_coach.get_coach_assignments),
    path("coach/session",                       views_coach.log_coach_session),
    path("coach/workout/generate",              views_coach.generate_workout_plan),

    # ── AI Insights ─────────────────────────────────────────────────────────
    path("ai/hps-explain/<str:user_id>",        views_ai.explain_hps_score),
    path("ai/interpret-report/<str:user_id>",   views_ai.interpret_lab_report),
    path("ai/chat-context/<str:patient_id>",    views_ai.get_ai_chat_context),
    path("ai/dropout-risk/<str:patient_id>",    views_ai.detect_dropout_risk),

    # ── Telehealth ──────────────────────────────────────────────────────────
    path("telehealth/token",                    views_telehealth.generate_telehealth_token),
    path("telehealth/status/<str:room_id>",     views_telehealth.get_telehealth_room_status),
    
    # ── Platform Admin / HRMS ───────────────────────────────────────────────
    path("admin/stats/platform",                views_admin.platform_stats),

    path("admin/announcements",                 views_admin.announcements),
    path("admin/announcements/active",          views_admin.announcements_active),
    path("admin/announcements/<str:ann_id>",    views_admin.announcements_detail),
    path("admin/announcements/<str:ann_id>/dismiss", views_admin.announcements_dismiss),
    path("admin/audit-logs",                    views_admin.get_audit_logs),
    path("admin/audit-logs/action-types",       views_admin.get_action_types),
    path("admin/hrms/leaves",                   views_admin.leave_management),
    path("admin/hrms/payroll",                  views_admin.payroll_records),
    path("admin/hrms/employees",                views_admin.manage_hrms_employees),
    path("admin/hrms/employees/<str:emp_id>",   views_admin.manage_hrms_employee_detail),
    path("admin/hrms/departments",              views_admin.manage_hrms_departments),
    path("admin/hrms/org-chart",                views_admin.manage_hrms_org_chart),
    path("admin/hrms/helpdesk",                 views_admin.helpdesk_tickets),
    path("admin/hrms/assets",                   views_admin.manage_assets),
    path("admin/hrms/assets/summary",           views_admin.asset_summary),
    path("admin/hrms/assets/<str:asset_id>/assign", views_admin.assign_asset),
    path("admin/hrms/assets/<str:asset_id>/unassign", views_admin.unassign_asset),
    path("admin/hrms/assets/<str:asset_id>/status", views_admin.update_asset_status),
    path("admin/bulk/role-change",              views_admin.bulk_role_change),
    path("admin/bulk/plan-change",              views_admin.bulk_plan_change),
    path("admin/bulk/status-change",            views_admin.bulk_status_change),
    path("admin/bulk/export-users",             views_admin.export_users_csv),
    path("admin/content",                       views_admin.content_list_create),
    path("admin/content/published",             views_admin.get_published_content),
    path("admin/content/<str:content_id>",      views_admin.content_detail),
    path("admin/corporates",                    views_admin.manage_corporates),
    path("admin/corporates/<str:corp_id>",      views_admin.get_corporate_detail),
    path("admin/financial/overview",            views_admin.financial_overview),
    path("admin/financial/subscriptions",       views_admin.subscription_details),
    
    # ── HPS Monitor ─────────────────────────────────────────────────────────
    path("admin/hps/distribution",              views_admin.hps_score_distribution),
    path("admin/hps/pillar-averages",           views_admin.hps_pillar_averages),
    path("admin/hps/calculation-logs",          views_admin.hps_calculation_logs),
    path("admin/hps/low-score-alerts",          views_admin.low_score_alerts),
    
    # ── Corporate / B2B ─────────────────────────────────────────────────────
    path("corp/dashboard",                      views_corp.corp_dashboard),
    
    # ── CXO / Executive Drilldowns ──────────────────────────────────────────
    path("cxo/strategic",                       views_corp.cxo_strategic_objectives),

    # ── Clinical / Operations ───────────────────────────────────────────────
    path("clinical/pharmacy",                   views_clinical.manage_pharmacy),
]
