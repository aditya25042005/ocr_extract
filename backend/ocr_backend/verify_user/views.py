# from django.shortcuts import render

# from rest_framework.generics import CreateAPIView
# from rest_framework.parsers import MultiPartParser, FormParser
# from rest_framework import status
# from rest_framework.views import APIView
# from .models import PassportRecord
# from .serializers import PassportReportSerializer

# from django.core.mail import send_mail
# import random
# import tempfile
# from rest_framework.response import Response
# from rest_framework.decorators import api_view
# from .models import EmailOTP
# from .serializers import EmailSerializer, OTPVerifySerializer

# # ❌ REMOVE HEAVY ML IMPORTS FROM HERE
# # from ML.aadhar_ocr import extract_aadhar_smart
# # from ML.handwritten_ocr import handwritten_extract
# # from ML.doc_verification import DocumentVerifier

# from django.core.files.temp import NamedTemporaryFile


# class PassportRecordCreateView(CreateAPIView):
#     queryset = PassportRecord.objects.all()
#     serializer_class = PassportReportSerializer
#     parser_classes = (MultiPartParser, FormParser)


# @api_view(['POST'])
# def send_otp(req):
#     serializer = EmailSerializer(data=req.data)
#     serializer.is_valid(raise_exception=True)
#     email = serializer.validated_data['email']
#     otp = str(random.randint(100000, 999999))
#     EmailOTP.objects.create(email=email, otp=otp)
#     send_mail(
#         subject="Your Login OTP",
#         message=f"Your OTP is {otp}. It is valid for 10 minutes.",
#         from_email=None,
#         recipient_list=[email],
#         fail_silently=False,
#     )
#     return Response({"message": "OTP sent successfully!"})


# @api_view(['POST'])
# def verify_otp(req):
#     serializer = OTPVerifySerializer(data=req.data)
#     serializer.is_valid(raise_exception=True)
#     email = serializer.validated_data["email"]
#     entered_otp = serializer.validated_data["otp"]

#     try:
#         otp_record = EmailOTP.objects.filter(email=email).latest("created_at")
#     except EmailOTP.DoesNotExist:
#         return Response({"error": "OTP not found"}, status=400)

#     if not otp_record.is_valid():
#         return Response({"error": "expired otp"}, status=400)
#     if entered_otp != otp_record.otp:
#         return Response({"error": "invalid otp"}, status=400)
#     return Response({"message": "OTP verified! User can now log in."})


# # -------------------------------------------
# #     LIGHTWEIGHT OCR ENDPOINTS (LAZY IMPORT)
# # -------------------------------------------

# @api_view(['POST'])
# def aadhar_ocr_view(request):

#     # ✔ LAZY IMPORT — loads CRAFT + TrOCR ONLY when needed
#     from ML.aadhar_ocr import extract_aadhar_smart

#     # Case 1: Cloudinary URL provided
#     if "url" in request.data:
#         image_url = request.data["url"]
#         temp_file = NamedTemporaryFile(delete=False)

#         # Download the image
#         import requests
#         resp = requests.get(image_url)
#         temp_file.write(resp.content)
#         temp_file.close()

#         result = extract_aadhar_smart(temp_file.name)
#         return Response(result)

#     # Case 2: File uploaded directly
#     file = request.FILES.get("file")
#     if not file:
#         return Response({"error": "Upload a file or send a URL"}, status=400)

#     temp_file = NamedTemporaryFile(delete=False)
#     for chunk in file.chunks():
#         temp_file.write(chunk)
#     temp_file.close()

#     result = extract_aadhar_smart(temp_file.name)
#     return Response(result)


# @api_view(['POST'])
# def handwritten_ocr_view(request):

#     # ✔ LAZY IMPORT HERE — loads handwritten TrOCR ONLY when needed
#     from ML.handwritten_ocr import handwritten_extract

#     file = request.FILES.get("file")
#     if not file:
#         return Response({"error": "Upload a file"}, status=400)

#     temp_file = NamedTemporaryFile(delete=False)
#     for chunk in file.chunks():
#         temp_file.write(chunk)
#     temp_file.close()

#     result = handwritten_extract(temp_file.name)
#     return Response(result)


# # -------------------------------------------
# #        DOCUMENT VERIFICATION VIEW
# # -------------------------------------------

# import os

# class DocumentVerifyView(APIView):

#     def post(self, request):
#         from ML.doc_verification import DocumentVerifier
#         from .serializers import DocumentVerifySerializer

#         serializer = DocumentVerifySerializer(data=request.data)

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         data = serializer.validated_data

#         # ----------------------------------------------------
#         # Save birth_doc with correct suffix (.pdf or .jpg)
#         # ----------------------------------------------------
#         birth_doc = data["birth_doc"]
#         birth_ext = os.path.splitext(birth_doc.name)[1] or ".pdf"

#         with tempfile.NamedTemporaryFile(delete=False, suffix=birth_ext) as birth_temp:
#             birth_temp.write(birth_doc.read())
#             birth_path = birth_temp.name

#         # ----------------------------------------------------
#         # Save id_doc with correct suffix (.pdf or .jpg)
#         # ----------------------------------------------------
#         id_doc = data["id_doc"]
#         id_ext = os.path.splitext(id_doc.name)[1] or ".pdf"

#         with tempfile.NamedTemporaryFile(delete=False, suffix=id_ext) as id_temp:
#             id_temp.write(id_doc.read())
#             id_path = id_temp.name

#         # User details
#         user_details = {
#             "first_name": data["first_name"],
#             "middle_name": data.get("middle_name", ""),
#             "last_name": data["last_name"],
#             "gender": data["gender"],
#             "dob": data["dob"],
#         }

#         try:
#             verifier = DocumentVerifier()
#             result = verifier.verify(birth_path, id_path, user_details)

#             return Response(
#                 {"status": "success", "verification_result": result},
#                 status=status.HTTP_200_OK
#             )

#         except Exception as e:
#             return Response(
#                 {"status": "error", "message": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

# @api_view(['POST'])
# def AadharDetectView(request):

#     # Lazy import to avoid loading YOLO at server startup
#     from ML.aadhaar_detector import is_aadhaar  

#     file = request.FILES.get("file")
#     if not file:
#         return Response({"error": "Upload a file"}, status=400)

#     # Save temporary file
#     temp_file = NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1])
#     for chunk in file.chunks():
#         temp_file.write(chunk)
#     temp_file.close()

#     # Run Aadhaar detection
#     result = is_aadhaar(temp_file.name)

#     return Response({
#         "is_aadhaar": result,
#         "message": "Aadhaar Card ✓" if result else "NOT Aadhaar Card ✗"
#     })

# @api_view(['POST'])
# def quality_score_view(request):
#     from ML.quality_score import process_uploaded_file, calc_scores

#     file = request.FILES.get("file")
#     if not file:
#         return Response({"error": "Upload a file"}, status=400)

#     try:
#         image = process_uploaded_file(file)
#         result = calc_scores(image)
#         return Response(result)

#     except Exception as e:
#         return Response({"error": str(e)}, status=500)

from django.shortcuts import render

from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.views import APIView
from .models import PassportRecord
from .serializers import PassportReportSerializer

from django.core.mail import send_mail
import random
import tempfile
import os

from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import EmailOTP
from .serializers import EmailSerializer, OTPVerifySerializer


# -------------------------------------------------------
#               PASSPORT RECORD CREATE VIEW
# -------------------------------------------------------

class PassportRecordCreateView(CreateAPIView):
    queryset = PassportRecord.objects.all()
    serializer_class = PassportReportSerializer
    parser_classes = (MultiPartParser, FormParser)


# -------------------------------------------------------
#                        OTP VIEWS
# -------------------------------------------------------

@api_view(['POST'])
def send_otp(req):
    serializer = EmailSerializer(data=req.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']

    otp = str(random.randint(100000, 999999))
    EmailOTP.objects.create(email=email, otp=otp)

    send_mail(
        subject="Your Login OTP",
        message=f"Your OTP is {otp}. It is valid for 10 minutes.",
        from_email=None,
        recipient_list=[email],
    )

    return Response({"message": "OTP sent successfully!"})


@api_view(['POST'])
def verify_otp(req):
    serializer = OTPVerifySerializer(data=req.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]
    entered_otp = serializer.validated_data["otp"]

    try:
        otp_record = EmailOTP.objects.filter(email=email).latest("created_at")
    except EmailOTP.DoesNotExist:
        return Response({"error": "OTP not found"}, status=400)

    if not otp_record.is_valid():
        return Response({"error": "expired otp"}, status=400)

    if entered_otp != otp_record.otp:
        return Response({"error": "invalid otp"}, status=400)

    return Response({"message": "OTP verified! User can now log in."})


# -------------------------------------------------------
#               OCR ENDPOINTS (LAZY IMPORT)
# -------------------------------------------------------

@api_view(['POST'])
def aadhar_ocr_view(request):
    from ML.aadhar_ocr import extract_aadhar_smart

    # Case 1: Cloudinary URL
    if "url" in request.data:
        import requests
        image_url = request.data["url"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            resp = requests.get(image_url)
            temp_file.write(resp.content)
            temp_path = temp_file.name

        result = extract_aadhar_smart(temp_path)
        return Response(result)

    # Case 2: File upload
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file or provide URL"}, status=400)

    suffix = os.path.splitext(file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    result = extract_aadhar_smart(temp_path)
    return Response(result)


@api_view(['POST'])
def handwritten_ocr_view(request):
    from ML.handwritten_ocr import handwritten_extract

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file"}, status=400)

    suffix = os.path.splitext(file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    result = handwritten_extract(temp_path)
    return Response(result)


# -------------------------------------------------------
#               DOCUMENT VERIFICATION VIEW
# -------------------------------------------------------

class DocumentVerifyView(APIView):
    def post(self, request):
        from ML.doc_verification import DocumentVerifier
        from .serializers import DocumentVerifySerializer

        serializer = DocumentVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Save birth_doc
        birth_doc = data["birth_doc"]
        birth_ext = os.path.splitext(birth_doc.name)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=birth_ext) as birth_temp:
            birth_temp.write(birth_doc.read())
            birth_path = birth_temp.name

        # Save id_doc
        id_doc = data["id_doc"]
        id_ext = os.path.splitext(id_doc.name)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=id_ext) as id_temp:
            id_temp.write(id_doc.read())
            id_path = id_temp.name

        # User details dict
        user_details = {
            "first_name": data["first_name"],
            "middle_name": data.get("middle_name", ""),
            "last_name": data["last_name"],
            "gender": data["gender"],
            "dob": data["dob"],
        }

        try:
            verifier = DocumentVerifier()
            result = verifier.verify(birth_path, id_path, user_details)

            return Response(
                {"status": "success", "verification_result": result},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# -------------------------------------------------------
#           AADHAAR DETECTION (YOLO)
# -------------------------------------------------------

@api_view(['POST'])
def AadharDetectView(request):
    from ML.aadhaar_detector import is_aadhaar  

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file"}, status=400)

    suffix = os.path.splitext(file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    result = is_aadhaar(temp_path)

    return Response({
        "is_aadhaar": result,
        "message": "Aadhaar Card ✓" if result else "NOT Aadhaar Card ✗"
    })


# -------------------------------------------------------
#           QUALITY SCORE VIEW
# -------------------------------------------------------

@api_view(['POST'])
def quality_score_view(request):
    from ML.quality_score import process_uploaded_file, calc_scores

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file"}, status=400)

    try:
        image = process_uploaded_file(file)
        result = calc_scores(image)
        return Response(result)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

