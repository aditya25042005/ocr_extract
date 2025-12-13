from django.urls import path
from .views import * 

urlpatterns = [
    path('passport/create/',PassportRecordCreateView.as_view(),name='passport-create'),
    path('passport/ids/',passport_ids_view,name='passport-ids'),
    path('passport/<int:id>/toggle-status/',update_passport_status),
    path('passport/<int:id>/',PassportRecordDetailView.as_view(),name='passport-detail'),
    path('send-otp/',send_otp),
    path('verify-otp/',verify_otp),
    path("aadhar/ocr/", aadhar_ocr_view),
    path("handwritten/ocr/", handwritten_ocr_view),
    path("verify-documents/", DocumentVerifyView.as_view(), name="verify-documents"),
    path("aadhaar-detect/", AadharDetectView,name="is-valid-aadhar"),
    path("quality-score/", quality_score_view),
]