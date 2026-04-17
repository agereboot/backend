from django.urls import path
from . import (
    views,
    views_biomarkers, views_hps, views_health, views_nutrition,
    views_emr, views_cc, views_telehealth, views_coach, views_ai,
    views_admin, views_corp, views_clinical,
    views_employee,
    views_corp_dashboard, views_corp_employees, views_corp_operations,
    views_corp_nudge, views_corp_intelligence, views_corp_data_quality,
    views_auth,
    views_video_consultation, views_patient_booking, views_patient_chat,
    views_longevity_protocol,
    views_notifications, views_outcome_learning,
    views_lab_ingestion, views_misc, views_coach_v2, views_roadmap
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
    
    # Legacy Auth Routes (Parity)
    path("api/auth/register", views_auth.register),
    path("api/auth/login", views_auth.login),
    path("auth/me", views_auth.get_me),
    path("api/auth/me", views_auth.get_me),
    path("api/auth/send-otp", views_auth.send_otp),
    path("api/auth/verify-otp", views_auth.verify_otp),
    path("dropdowns/locations/", views.location_dropdown_api),
    path("dropdowns/departments/", views.department_dropdown_api),
    path("dropdowns/status/", views.status_dropdown_api),
    path("hr/challenges/", views.create_daily_challenge),
    path("hr/challenges/list/", views.hr_challenges_list),
    path("hr/challenges/<int:id>/participants/", views.challenge_participants),
    path("employee/challenges/", views.employee_challenges),
    path("employee/challenges/<uuid:id>/join", views.join_daily_challenge),
    path("employee/challenges/<uuid:id>/progress", views.update_daily_progress),

    # ── Role ──
    path("roles/",              views.RoleListCreateView.as_view(),    name="admin-role-list"),
    path("roles/<int:pk>/",     views.RoleDetailView.as_view(),        name="admin-role-detail"),

    # ── Company ──
    path("companies/",          views.CompanyListCreateView.as_view(), name="admin-company-list"),
    path("companies/<int:pk>/", views.CompanyDetailView.as_view(),     name="admin-company-detail"),

    # ── Location ──
    path("locations/",          views.LocationListCreateView.as_view(),  name="admin-location-list"),
    path("locations/<int:pk>/", views.LocationDetailView.as_view(),      name="admin-location-detail"),

    # ── Department ──
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

    # path('credits/', views.get_credits, name='get_credits'),
    path('credits/', views.get_credits, name='get_credits'),
    path('credits/purchase', views.purchase_credits_mock, name='purchase_credits'),

    # ── Biomarkers ──────────────────────────────────────────────────────────
    # path("biomarkers/ingest",                   views_biomarkers.ingest_biomarkers),
    # path("biomarkers/definitions/all",          views_biomarkers.get_biomarker_definitions),
    # path("biomarkers/pillar-dashboard",         views_biomarkers.get_pillar_dashboard),
    # path("biomarkers/manual-entry",             views_biomarkers.create_manual_entry),
    # path("biomarkers/manual-entries",           views_biomarkers.get_manual_entries),
    # path("biomarkers/<str:user_id>",            views_biomarkers.get_user_biomarkers),
    # path("wearable/connections",                views_biomarkers.get_connections),
    # path("lab/upload",                          views_biomarkers.upload_lab_results),

    # Legacy Biomarker Routes (Parity)
    path("biomarkers/ingest",               views_biomarkers.ingest_biomarkers),
    path("biomarkers/definitions/all",      views_biomarkers.get_biomarker_definitions),
    path("biomarkers/compare",              views_biomarkers.compare_biomarkers),
    path("biomarkers/pillar-dashboard",     views_biomarkers.get_pillar_dashboard),
    path("biomarkers/predictions",           views_biomarkers.get_biomarker_predictions),
    path("biomarkers/cognitive-assessments", views_biomarkers.get_cognitive_assessments),
    path("biomarkers/cognitive-assessments/submit", views_biomarkers.submit_cognitive_assessment),
    path("biomarkers/manual-entry",         views_biomarkers.create_manual_entry),
    path("biomarkers/manual-entry/<str:entry_id>/validate", views_biomarkers.validate_manual_entry),
    path("biomarkers/manual-entries",       views_biomarkers.get_manual_entries),
    path("biomarkers/correlation-matrix",   views_biomarkers.get_correlation_matrix),
    path("biomarkers/benchmarking",         views_biomarkers.get_biomarker_benchmarking),
    path("biomarkers/<str:user_id>",        views_biomarkers.get_user_biomarkers),
    path("wearable/devices",                views_biomarkers.get_wearable_devices),
    path("wearable/sync",                   views_biomarkers.sync_wearable),
    path("lab/upload",                      views_biomarkers.upload_lab_results),
    path("lab/upload-text",                 views_biomarkers.upload_lab_text),
    path("wearable/connections",            views_biomarkers.get_connections),
    path("wearable/connect/<str:device>",   views_biomarkers.connect_device),
    path("wearable/disconnect/<str:device>", views_biomarkers.disconnect_device),
    path("reports/repository",              views_biomarkers.get_report_repository),
    path("reports/upload",                  views_biomarkers.upload_report),
    path("patient/biomarker-analytics",     views_biomarkers.get_biomarker_analytics),
    path("patient/<str:member_id>/biomarker-analytics", views_biomarkers.get_biomarker_analytics),
    path("patient/<str:member_id>/medical-history", views_emr.medical_history_parity),
    path("patient/messaging/send", views_cc.send_secure_message_parity),
    path("patient/messaging/<str:member_id>", views_cc.get_messaging_thread_parity),


    # ── HPS ─────────────────────────────────────────────────────────────────
    path("hps/compute",                         views_hps.compute_hps_score),
    path("hps/score/<str:user_id>",             views_hps.get_hps_score),
    path("hps/history/<str:user_id>",           views_hps.get_hps_history),
    path("hps/predict/<str:user_id>",           views_hps.predict_hps),
    path("hps/trend",                           views_hps.get_hps_trend),
    path("hps/adaptive-assessment/questions", views_hps.get_adaptive_questions),
    path("hps/adaptive-assessment/submit",    views_hps.submit_adaptive_assessment),
    path("hps/adaptive-assessment/latest",    views_hps.get_latest_adaptive_assessment),
    path("hps/adaptive-assessment/history",   views_hps.get_adaptive_assessment_history),


    # ── Health ──────────────────────────────────────────────────────────────
    path("health/organ-ages",                   views_health.predict_organ_ages),
    path("health/records",                      views_health.get_health_records),
    path("health/records/summary",              views_health.get_health_summary),
    path("health/overview",                     views_health.get_health_overview),
    path("health/appointments/book",            views_health.book_appointment),
    path("health/appointments/<str:apt_id>/reschedule", views_health.reschedule_appointment),
    path("health/medications/<uuid:med_id>/log", views_health.log_medication),
    path("health/medications/<uuid:med_id>/refill", views_health.request_medication_refill),
    path("health/digest/send",                  views_health.send_health_digest),
    path("employee/sos",                        views_health.trigger_sos),

    # ── Nutrition ───────────────────────────────────────────────────────────
    path("nutrition/plan",                      views_nutrition.get_nutrition_plan),
    path("nutrition/log",                       views_nutrition.log_nutrition),
    path("nutrition/logs",                      views_nutrition.get_nutrition_logs),
    path("nutrition/trends",                    views_nutrition.get_nutrition_trends),
    path("nutrition/gap-adjustment",        views_nutrition.get_gap_adjustment),
    path("nutrition/intake-flags",          views_nutrition.get_intake_flags),
    path("nutrition/analyze-photo",         views_nutrition.analyze_meal_photo),
    path("nutrition/weekly-score",          views_nutrition.get_weekly_nutrition_score),

    # ── EMR ─────────────────────────────────────────────────────────────────
    path("emr/history",                         views_emr.get_medical_history),
    path("emr/history/update",                  views_emr.update_medical_history),
    path("emr/encounter",                       views_emr.create_emr_encounter),
    path("emr/encounter/<str:member_id>",       views_emr.get_member_encounters),
    path("emr/encounter/detail/<str:encounter_id>", views_emr.get_encounter_detail),
    path("emr/member/<str:member_id>/chart",    views_emr.get_patient_chart),
    path("emr/member/<str:member_id>/problems", views_emr.get_member_problems),
    path("emr/member/<str:member_id>/problems/add", views_emr.add_problem),
    path("emr/member/<str:member_id>/problems/<str:problem_id>", views_emr.update_problem),
    path("emr/member/<str:member_id>/problems/<str:problem_id>/delete", views_emr.delete_problem),
    path("emr/member/<str:member_id>/medications", views_emr.get_member_medications),
    path("emr/member/<str:member_id>/medications/add", views_emr.add_medication),
    path("emr/member/<str:member_id>/allergies", views_emr.get_member_allergies),
    path("emr/member/<str:member_id>/allergies/add", views_emr.add_allergy),
    path("emr/lab-orders",                      views_emr.get_lab_orders),
    path("emr/lab-orders/create",               views_emr.create_lab_order),
    path("emr/lab-orders/<str:order_id>",       views_emr.get_lab_order_detail),
    path("emr/lab-panels",                      views_emr.list_lab_panels),
    path("emr/lab-orders/<str:order_id>/status", views_emr.update_lab_order_status),
    path("emr/lab-orders/<str:order_id>/results", views_emr.upload_lab_results),
    path("emr/e-prescribe",                     views_emr.create_prescription),
    path("emr/prescriptions",                   views_emr.list_prescriptions),
    path("emr/prescriptions/<str:rx_id>",       views_emr.update_prescription),
    path("emr/prescriptions/<str:rx_id>/refill", views_emr.refill_prescription),
    path("emr/member/<str:member_id>/visit-summary", views_emr.get_visit_summary),
    path("emr/encounters/smart",                views_emr.create_smart_encounter),
    path("emr/member/<str:member_id>/hps-profile", views_emr.get_member_hps_profile),
    path("emr/member/<str:member_id>/hps-delta", views_emr.get_hps_delta),
    path("emr/drugs/search",                    views_emr.search_drugs),
    path("emr/diagnostics/search",               views_emr.search_diagnostics),
    path("emr/diagnostics/create",              views_emr.create_diagnostic_order),
    path("emr/member/<str:member_id>/smart-protocols", views_emr.get_smart_protocols),
    path("emr/hcp-coaches",                     views_emr.list_hcp_coaches),
    path("emr/member/<str:member_id>/medical-history", views_emr.get_medical_history),
    path("emr/member/<str:member_id>/vitals-history", views_emr.get_vitals_history),
    path("emr/vitals-log",                      views_emr.record_vitals_log),
    path("emr/member/<str:member_id>/cdss-suggestions", views_emr.get_cdss_suggestions),
    path("emr/member/<str:member_id>/care-plan", views_emr.get_emr_care_plan),
    path("emr/member/<str:member_id>/longevity-roadmap", views_emr.get_longevity_roadmap),
    path("emr/member/<str:member_id>/longevity-roadmap/approve", views_emr.approve_longevity_protocols),
    # ── EMR Appointments Parity ────────────────────────────────────────────
    path("emr/appointments",                    views_emr.list_appointments_parity),
    path("emr/appointments/create",             views_emr.create_appointment_parity),
    path("emr/appointments/<uuid:appt_id>",     views_emr.get_appointment_detail_parity),
    path("emr/member/<str:member_id>/longevity-roadmap/approve", views_emr.approve_longevity_protocols),

    # ── Care Coordination (CC) Parity ──────────────────────────────────────
    path("cc/dashboard",                    views_cc.cc_dashboard),
    path("cc/members",                      views_cc.get_cc_members),
    path("cc/members/<str:member_id>",      views_cc.get_member_detail),
    path("cc/alerts",                       views_cc.get_cc_alerts),
    path("cc/alerts/<str:alert_id>/resolve",views_cc.resolve_cc_alert),
    path("cc/protocols",                    views_cc.get_cc_protocols),
    path("cc/protocols/<str:protocol_id>/prescribe", views_cc.prescribe_protocol),
    path("cc/members/<str:member_id>/care-plan", views_cc.member_care_plan),
    path("cc/sessions/member/<str:member_id>", views_cc.get_member_cc_sessions),
    path("cc/sessions/log",                  views_cc.log_cc_session),
    path("cc/messages/<str:member_id>",      views_cc.get_cc_messages),
    path("cc/messages/send",                 views_cc.send_cc_message),
    path("cc/override",                      views_cc.cc_override_hps),
    path("cc/cdss/<str:member_id>",          views_cc.cdss_analyze),
    path("cc/members/<str:member_id>/protocol-recommendations", views_cc.get_protocol_recommendations),
    path("cc/bio-age/<str:member_id>",       views_cc.get_bio_age),
    path("cc/population-health",             views_cc.population_health),
    path("cc/revenue-analytics",             views_cc.revenue_analytics),
    path("cc/clinical-kpis",                 views_cc.clinical_kpis),
    path("cc/role-meta",                     views_cc.get_role_metadata),
    path("cc/role-dashboard",                views_cc.role_intelligent_dashboard),
    path("cc/members/<str:member_id>/hallmarks", views_cc.get_member_hallmarks),
    path("cc/referrals",                     views_cc.cc_referrals),
    path("cc/ai-priority-feed",              views_cc.ai_priority_feed),
    path("cc/lab-partners",                  views_clinical.list_lab_partners),
    path("cc/pharmacy/catalog",              views_clinical.get_pharmacy_catalog),
    path("cc/pharmacy/orders",                views_clinical.pharmacy_orders_view),

    path("cc/nfle/tasks",                   views_cc.get_nfle_tasks),
    
    # Roadmap & Messaging (New Parity)
    path("roadmap/pending-reviews",     views_longevity_protocol.get_pending_reviews),
    path("roadmap/all-reviews",         views_roadmap.get_all_reviews),
    path("roadmap/generate",            views_roadmap.generate_roadmap),
    path("roadmap/submit-for-review",   views_roadmap.submit_roadmap_for_review),
    path("roadmap/<uuid:user_id>",      views_roadmap.get_roadmap),
    path("roadmap/<uuid:review_id>/approve", views_roadmap.approve_roadmap),
    path("roadmap/<uuid:review_id>/reject",  views_roadmap.reject_roadmap),
    path("roadmap/review-history/<uuid:user_id>", views_roadmap.get_review_history),

    path("patient/messaging/conversations", views_patient_chat.get_conversations),
    path("patient/messaging/send",          views_cc.send_secure_message_parity),
    path("patient/messaging/<int:member_id>", views_cc.get_messaging_thread_parity),



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
    
    # ── Video Consultation Parity ──────────────────────────────────────────
    path("video-consultation/available-slots/<str:doctor_id>", views_video_consultation.get_available_slots),
    path("video-consultation/book",         views_video_consultation.book_consultation),
    path("video-consultation/my-consultations", views_video_consultation.get_my_consultations),
    path("video-consultation/consultation/<uuid:consultation_id>", views_video_consultation.get_consultation_detail),
    path("video-consultation/join/<uuid:consultation_id>", views_video_consultation.join_consultation),
    path("video-consultation/end/<uuid:consultation_id>", views_video_consultation.end_consultation),
    path("video-consultation/biomarker-panels", views_video_consultation.get_biomarker_panels),
    path("video-consultation/cancel/<uuid:consultation_id>",
         views_video_consultation.cancel_consultation),
 
    path("video-consultation/reschedule/<uuid:consultation_id>",
         views_video_consultation.reschedule_consultation),

    # ── Patient Booking Parity ─────────────────────────────────────────────
    path("patient-booking/available-slots",           views_patient_booking.get_available_booking_slots),
    path("patient-booking/book",            views_patient_booking.book_sample_collection),
    path("patient-booking/my-bookings",     views_patient_booking.get_my_bookings),
    path("patient-booking/post-consultation", views_patient_booking.get_post_consultation_info),

    # ── Patient Chat Parity ────────────────────────────────────────────────
    path("patient-chat/threads",                    views_patient_chat.get_chat_threads),
    path("patient-chat/threads/<int:thread_id>/messages", views_patient_chat.get_thread_messages),
    path("patient-chat/threads/<int:thread_id>/send",     views_patient_chat.send_message),

    # ── Longevity Protocol Parity ──────────────────────────────────────────
    path("longevity-protocol/generate/<str:patient_id>", views_longevity_protocol.generate_longevity_protocol),
    path("longevity-protocol/my-protocol",   views_longevity_protocol.get_my_active_protocol),
    path("ongevity-protocol/ninety-day-check", views_longevity_protocol.check_ninety_day_cycle),
    path("longevity-protocol/post-call-actions/<uuid:consultation_id>", views_longevity_protocol.get_post_call_actions),

    # ── Notifications Parity ───────────────────────────────────────────────
    path("notifications",                   views_notifications.get_notifications),
    path("notifications/count",             views_notifications.get_unread_count),
    path("notifications/<uuid:notification_id>/read", views_notifications.mark_notification_read),
    path("notifications/read-all",          views_notifications.mark_all_read),
    path("notifications/create",            views_notifications.create_notification),
    path("notifications/bulk-create",       views_notifications.create_bulk_notifications),

    # ── Outcome Learning & Health Brief Parity ─────────────────────────────
    path("api/outcome/record-cycle/<str:patient_id>", views_outcome_learning.record_outcome_cycle),
    path("api/outcome/cycles/<str:patient_id>",       views_outcome_learning.get_outcome_cycles),
    path("api/health-brief/generate/<str:patient_id>", views_outcome_learning.generate_health_brief),
    path("api/health-brief/latest/<str:patient_id>",   views_outcome_learning.get_latest_health_brief),

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
    path("admin/hrms/assets/<str:asset_id>/assign",   views_admin.assign_asset),
    path("admin/hrms/assets/<str:asset_id>/unassign", views_admin.unassign_asset),
    path("admin/hrms/assets/<str:asset_id>/status",   views_admin.update_asset_status),
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
    
    # ── Corporate Dashboard ──
    path("corporate/dashboard", views_corp_dashboard.get_corporate_dashboard),
    
    # ── Corporate Employees ──
    path("corporate/employees", views_corp_employees.get_employees),
    path("corporate/employees/<str:emp_id>", views_corp_employees.get_employee_detail),
    path("corporate/engagement/overview", views_corp_employees.get_engagement_overview),
    path("corporate/engagement/inactive", views_corp_employees.get_inactive_employees),
    path("corporate/burnout/overview", views_corp_employees.get_burnout_overview),
    path("corporate/burnout/intervene", views_corp_employees.create_intervention),
    path("corporate/departments", views_corp_employees.get_department_analytics),
    path("corporate/outliers", views_corp_employees.get_outliers),
    
    # ── Corporate Operations ──
    path("corporate/profit-share", views_corp_operations.get_profit_share),
    path("corporate/franchise", views_corp_operations.get_franchise_status),
    path("corporate/programmes", views_corp_operations.get_programmes),
    path("corporate/analytics/roi", views_corp_operations.get_roi_analytics),
    path("corporate/seasons", views_corp_operations.get_seasons),
    path("corporate/qualification-tracker", views_corp_operations.get_qualification_tracker),
    
    # ── Corporate Nudge ──
    path("corporate/nudge/segments", views_corp_nudge.get_nudge_segments),
    path("corporate/nudge/segments/<str:segment_id>/employees", views_corp_nudge.get_segment_employees_view),
    path("corporate/nudge/campaigns", views_corp_nudge.get_nudge_campaigns),
    path("corporate/nudge/campaigns/create", views_corp_nudge.create_nudge_campaign),
    
    # ── Corporate Intelligence ──
    path("corporate/organogram", views_corp_intelligence.get_organogram),
    path("corporate/hr-escalations", views_corp_intelligence.get_hr_escalations),
    path("corporate/hr-escalations/<str:esc_id>", views_corp_intelligence.update_hr_escalation),
    path("corporate/manager-view/<str:dept_name>", views_corp_intelligence.get_manager_view),
    path("corporate/subscriptions", views_corp_intelligence.get_subscriptions),
    path("corporate/ai-hub", views_corp_intelligence.get_ai_hub),
    path("corporate/analytics/benchmarks", views_corp_intelligence.get_benchmarks),
    
    # ── Corporate Data Quality ──
    path("corporate/data-quality", views_corp_data_quality.get_data_quality_dashboard),
    path("corporate/data-quality/nudge", views_corp_data_quality.send_data_quality_nudge),
    path("corporate/escalate-to-care-team", views_corp_data_quality.escalate_to_care_team),
    path("corporate/care-team-escalations", views_corp_data_quality.get_care_team_escalations),

    # ── Clinical / Command Centre (CC) ───────────────────────────────────────
    path("cc/lab-partners",               views_clinical.list_lab_partners),
    path("cc/lab-panels",                 views_clinical.list_lab_panels),
    path("cc/lab-orders",                 views_clinical.lab_orders_view),
    path("cc/lab-orders/<str:order_id>",  views_clinical.get_lab_order_detail),
    path("cc/lab-orders/<str:order_id>/status", views_clinical.update_lab_order_status),
    path("cc/lab-orders/<str:order_id>/results", views_clinical.upload_lab_results),
    path("cc/pharmacy/catalog",           views_clinical.get_pharmacy_catalog),
    path("cc/pharmacy/orders",            views_clinical.pharmacy_orders_view),
    path("cc/pharmacy/orders/<str:order_id>", views_clinical.get_pharmacy_order_detail),
    path("cc/pharmacy/orders/<str:order_id>/status", views_clinical.update_pharmacy_order_status),

    # ════════════════════════════════════════════════════════════════════════
    # Employee Portal  (views_employee.py — all 28 endpoints)
    # ════════════════════════════════════════════════════════════════════════

    # Dashboard & global ranking
    path("employee/dashboard-stats",            views_employee.dashboard_stats),
    path("employee/global-ranking",             views_employee.global_ranking),

    # Daily challenge
    path("employee/daily-challenge",            views_employee.get_daily_challenge),
    path("employee/daily-challenge/complete",   views_employee.complete_daily_challenge),

    # Action items & streak calendar
    path("employee/action-items",               views_employee.get_action_items),
    path("employee/streak-calendar",            views_employee.streak_calendar),

    # Address
    path("employee/address",                    views_employee.get_address),
    path("employee/address/update",             views_employee.update_address),

    # Challenges (employee view — listing + join + progress)
    # path("employee/challenges/list",            views_employee.list_challenges),
    # path("employee/challenges/<int:challenge_id>/join",     views.join_challenge),
    # path("employee/challenges/<int:challenge_id>/progress", views.update_challenge_progress),

    # Rewards & badges
    path("rewards/badges",                      views_employee.get_badge_catalog),
    path("rewards/my-badges",                   views_employee.get_my_badges),

    # Social feed  (order: specific before generic <str> wildcards)
    path("feed/highlights",                     views_employee.get_feed_highlights),
    path("feed/post",                           views_employee.create_feed_post),
    path("feed/upload-photo",                   views_employee.upload_feed_photo),
    path("feed/photo/<str:photo_id>",           views_employee.serve_feed_photo),
    path("feed/<str:item_id>/like",             views_employee.like_feed_item),
    path("feed/<str:item_id>/comment",          views_employee.comment_on_feed),
    path("feed",                                views_employee.get_feed),

    # Profile photos
    path("profile/upload-photo",               views_employee.upload_profile_photo),
    path("profile/photo/<str:user_id>",        views_employee.serve_profile_photo),

    # Leaderboard
    path("leaderboard/franchises",             views_employee.franchise_leaderboard),
    path("leaderboard",                        views_employee.leaderboard),

    # Health Snapshots  (specific before wildcard)
    path("health-snapshots/upload",            views_employee.upload_health_snapshot),
    path("health-snapshots/photo/<str:snap_id>", views_employee.serve_snapshot_photo),
    path("health-snapshots/<str:snap_id>",     views_employee.delete_health_snapshot),
    path("health-snapshots",                   views_employee.get_health_snapshots),

    # ── Lab Ingestion (Parity) ──────────────────────────────────────────────
    path("lab-ingestion/upload-report",        views_lab_ingestion.upload_lab_report),
    path("lab-ingestion/reports/<str:patient_id>", views_lab_ingestion.get_patient_reports),
    path("lab-ingestion/report/<str:report_id>", views_lab_ingestion.get_report_detail),
    path("lab-ingestion/report/<str:report_id>/approve", views_lab_ingestion.approve_report_values),
    path("lab-ingestion/webhook/lab-partner",  views_lab_ingestion.lab_partner_webhook),

    # ── Miscellaneous (Parity) ──────────────────────────────────────────────
    # Mental Health
    path("health/mental-assessment/questions", views_misc.get_mental_health_questions),
    path("health/mental-assessment/submit",    views_misc.submit_mental_health_assessment),
    path("health/mental-assessment/history",   views_misc.get_mental_health_history),
    path("health/mental-assessment/ai-analysis", views_misc.get_mental_health_ai_analysis),
    path("health/mental-health/roadmap",       views_misc.get_mental_health_roadmap),
    path("health/burnout-prediction",          views_misc.predict_burnout),

    # Care Team
    path("care-team",                          views_misc.get_care_team),
    path("care-team/appointments",             views_misc.manage_care_appointments),
    path("care-team/reviews",                  views_misc.manage_care_reviews),

    # Settings & Profile
    path("settings/privacy",                   views_misc.privacy_settings),
    path("profile",                            views_misc.update_profile),

    # Credits
    path("credits/purchase",                   views_misc.purchase_credits),

    # Franchise & Seasons
    path("franchise/list",                     views_misc.list_franchises),
    path("franchise/dashboard/<str:franchise_name>", views_misc.franchise_dashboard),
    path("seasons",                            views_misc.manage_seasons),
    path("seasons/<uuid:season_id>/join",      views_misc.join_season),
    path("seasons/<uuid:season_id>/standings", views_misc.season_standings),

    # ── Coach Platform (CIP) ──────────────────────────────────────────────
    path("coach/tasks",                       views_coach.get_task_queue),
    path("coach/tasks/<uuid:task_id>/complete", views_coach.complete_task),
    path("coach/dashboard",                   views_coach.get_coach_dashboard),
    path("coach/messages",                    views_coach.manage_coach_messages),
    
    # PFC
    path("coach/pfc/fitness-profile/<str:member_id>", views_coach.get_fitness_profile),
    path("coach/pfc/programmes",              views_coach.get_programmes),
    path("coach/pfc/programmes/create",        views_coach.create_programme),
    path("coach/pfc/programmes/<uuid:prog_id>/approve", views_coach.approve_programme),
    path("coach/pfc/session-log",              views_coach.log_pfc_session),
    path("coach/pfc/wearable-feed",           views_coach.get_pfc_wearable_feed),
    
    # PSY
    path("coach/psy/assessment-templates",    views_coach.get_assessment_templates),
    path("coach/psy/assessments/<str:member_id>", views_coach.manage_psy_assessments),
    path("coach/psy/assessments/<uuid:assessment_id>/interpret", views_coach.interpret_assessment),
    path("coach/psy/cbt-modules",             views_coach.get_psy_cbt_modules),
    path("coach/psy/cbt-assign",              views_coach.assign_cbt_module),
    path("coach/psy/crisis-alerts",           views_coach.get_crisis_alerts),
    path("coach/psy/crisis-alerts/<uuid:alert_id>/resolve", views_coach.resolve_crisis_alert),
    
    # NUT
    path("coach/nut/nutritional-profile/<str:member_id>", views_coach.get_nutritional_profile),
    path("coach/nut/meal-plans",              views_coach.list_nut_meal_plans),
    path("coach/nut/meal-plans/create",       views_coach.create_meal_plan),
    path("coach/nut/supplements",             views_coach.manage_nut_supplements),

    # ── Coach Features V2 ──────────────────────────────────────────────
    path("coach-v2/habits/templates",         views_coach_v2.get_habit_templates),
    path("coach-v2/habits/assign",            views_coach_v2.assign_habit),
    path("coach-v2/habits/<str:member_id>",   views_coach_v2.get_member_habits),
    path("coach-v2/check-ins",                views_coach_v2.create_check_in),
    path("coach-v2/check-ins/<str:member_id>", views_coach_v2.get_check_ins),
    path("coach-v2/goals",                    views_coach_v2.create_goal),
    path("coach-v2/goals/<str:member_id>",    views_coach_v2.get_member_goals),
    path("coach-v2/goals/<uuid:goal_id>/progress", views_coach_v2.update_goal_progress),
    path("coach-v2/compliance/<str:member_id>", views_coach_v2.get_compliance_stats),
    path("coach-v2/challenges",               views_coach_v2.manage_challenges),
    path("coach-v2/challenges/<uuid:challenge_id>/leaderboard", views_coach_v2.get_challenge_leaderboard),
    path("coach-v2/psy/session-notes",        views_coach_v2.create_therapy_note),
    path("coach-v2/psy/session-notes/<str:member_id>", views_coach_v2.get_therapy_notes),
    path("coach-v2/psy/behavior/<str:member_id>", views_coach_v2.manage_behavior_logs),
    path("coach-v2/psy/therapy-programs",      views_coach_v2.manage_therapy_programs),
    path("coach-v2/nut/body-comp",            views_coach_v2.log_body_comp),
    path("coach-v2/nut/body-comp/<str:member_id>", views_coach_v2.get_body_comp),
    path("coach-v2/nut/consultation-notes/<str:member_id>", views_coach_v2.manage_nutrition_notes),
    path("coach-v2/nut/meal-plan-detail/<uuid:plan_id>", views_coach_v2.get_meal_plan_detail),
    path("coach-v2/nut/meal-plan-days",        views_coach_v2.save_meal_plan_day),
    path("coach-v2/profile",                   views_coach_v2.manage_coach_profile),
    path("coach-v2/performance",               views_coach_v2.get_coach_performance),
    path("coach-v2/alerts",                    views_coach_v2.get_role_alerts),
    path("coach-v2/escalations",               views_coach_v2.list_escalations),
    path("coach-v2/escalations/<uuid:escalation_id>/respond", views_coach_v2.respond_to_escalation),
    path("coach-v2/simplified-hps/<str:member_id>", views_coach_v2.get_simplified_hps),
    path("coach-v2/corporate-wellness",        views_coach_v2.get_corporate_wellness_v2),
]
