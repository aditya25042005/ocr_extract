from django.shortcuts import render

from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser,FormParser
from .models import PassportRecord
from .serializers import PassportReportSerializer

class PassportRecordCreateView(CreateAPIView):
    queryset=PassportRecord.objects.all()
    serializer_class=PassportReportSerializer
    parser_classes=(MultiPartParser,FormParser)
