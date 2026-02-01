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


]
