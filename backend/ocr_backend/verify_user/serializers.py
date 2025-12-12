from rest_framework import serializers
from .models import PassportRecord

class PassportReportSerializer(serializers.ModelSerializer):
    class Meta:
        model=PassportRecord
        fields="__all__"

class EmailSerializer(serializers.Serializer):
    email=serializers.EmailField()

class OTPVerifySerializer(serializers.Serializer):
    email=serializers.EmailField()
    otp=serializers.CharField(max_length=6)

class DocumentVerifySerializer(serializers.Serializer):
    # --- Personal Details ---
    first_name = serializers.CharField()
    middle_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField()
    gender = serializers.CharField()
    dob = serializers.CharField()

    # --- Address Fields (ALL REQUIRED) ---
    address_line = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    pincode = serializers.CharField()
    country = serializers.CharField()

    # --- Documents (3 required docs) ---
    dob_proof = serializers.FileField()
    id_proof = serializers.FileField()
    address_proof = serializers.FileField()
