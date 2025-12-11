from django.urls import path
from .views import * 

urlpatterns = [
    path('passport/create/',PassportRecordCreateView.as_view(),name='passport-create'),
    path('send-otp/',send_otp),
    path('verify-otp/',verify_otp),
    path("aadhar/ocr/", aadhar_ocr_view),
    path("handwritten/ocr/", handwritten_ocr_view),
    path("verify-documents/", DocumentVerifyView.as_view(), name="verify-documents")
]