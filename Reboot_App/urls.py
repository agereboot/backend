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
   


]
