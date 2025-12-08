from rest_framework import serializers
from .models import PassportRecord

class PassportReportSerializer(serializers.ModelSerializer):
    class Meta:
        model=PassportRecord
        fields="__all__"