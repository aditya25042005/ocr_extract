from django.urls import path
from .views import * 

urlpatterns = [
    path('passport/create/',PassportRecordCreateView.as_view(),name='passport-create'),
    path('send-otp/',send_otp),
    path('verify-otp/',verify_otp)
]