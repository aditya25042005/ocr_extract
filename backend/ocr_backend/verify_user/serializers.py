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

