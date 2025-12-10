from django.shortcuts import render

from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser,FormParser
from .models import PassportRecord
from .serializers import PassportReportSerializer

from django.core.mail import send_mail
import random
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import EmailOTP
from .serializers import EmailSerializer,OTPVerifySerializer

from ML.aadhar_ocr import extract_aadhar_smart
from django.core.files.temp import NamedTemporaryFile

from ML.handwritten_ocr import handwritten_extract


class PassportRecordCreateView(CreateAPIView):
    queryset=PassportRecord.objects.all()
    serializer_class=PassportReportSerializer
    parser_classes=(MultiPartParser,FormParser)

@api_view(['POST'])
def send_otp(req):
    serializer=EmailSerializer(data=req.data)
    serializer.is_valid(raise_exception=True)
    email=serializer.validated_data['email']
    otp=str(random.randint(100000,999999))
    EmailOTP.objects.create(email=email,otp=otp)
    send_mail(
        subject="Your Login OTP",
        message=f"Your OTP is {otp}. It is valid for 10 minutes.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
    return Response({"message": "OTP sent successfully!"})

@api_view(['POST'])
def verify_otp(req):
    serializer=OTPVerifySerializer(data=req.data)
    serializer.is_valid(raise_exception=True)
    email=serializer.validated_data["email"]
    entered_otp=serializer.validated_data["otp"]

    try:
        otp_record=EmailOTP.objects.filter(email=email).latest("created_at")
    except EmailOTP.DoesNotExist:
        return Response({"error":"OTP not found"},status=400)
    
    if not otp_record.is_valid():
        return Response({"error":"expired otp"},status=400)
    if entered_otp != otp_record.otp:
        return Response({"error":"invalid otp"},status=400)
    return Response({"message": "OTP verified! User can now log in."})

@api_view(['POST'])
def aadhar_ocr_view(request):
    # Case 1: Cloudinary URL provided
    if "url" in request.data:
        image_url = request.data["url"]
        temp_file = NamedTemporaryFile(delete=False)

        # Download the image from Cloudinary
        resp = request.get(image_url)
        temp_file.write(resp.content)
        temp_file.close()

        result = extract_aadhar_smart(temp_file.name)
        return Response(result)

    # Case 2: File uploaded directly
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file or send a URL"}, status=400)

    temp_file = NamedTemporaryFile(delete=False)
    for chunk in file.chunks():
        temp_file.write(chunk)
    temp_file.close()

    result = extract_aadhar_smart(temp_file.name)
    return Response(result)

@api_view(['POST'])
def handwritten_ocr_view(request):
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file"}, status=400)

    temp_file = NamedTemporaryFile(delete=False)
    for chunk in file.chunks():
        temp_file.write(chunk)
    temp_file.close()

    result = handwritten_extract(temp_file.name)
    return Response(result)


