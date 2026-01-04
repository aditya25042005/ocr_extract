from django.shortcuts import render
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.views import APIView
from .models import PassportRecord
from .serializers import PassportReportSerializer
from django.shortcuts import get_object_or_404

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
    from ml.aadhar_ocr import extract_fields_with_coords, run_ocr_pipeline

    # Case 1: Cloudinary URL
    if "url" in request.data:
        import requests
        image_url = request.data["url"]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            resp = requests.get(image_url)
            temp_file.write(resp.content)
            temp_path = temp_file.name

        ocr_lines = run_ocr_pipeline(temp_path)
        if ocr_lines:
            result = extract_fields_with_coords(ocr_lines)
            return Response(result)
        return Response({"message": "error in image detection"}, status=400)

    # Case 2: File upload
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file or provide URL"}, status=400)

    suffix = os.path.splitext(file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_path = temp_file.name

    ocr_lines = run_ocr_pipeline(temp_path)
    if ocr_lines:
        result = extract_fields_with_coords(ocr_lines)
        return Response(result)
    return Response ({"error": "error in pdf parsing"}, status= 400)


@api_view(['POST'])
def handwritten_ocr_view(request):
    from ml.handwritten_ocr import handwritten_extract

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
        from ml.doc_verification import DocumentVerifier
        from .serializers import DocumentVerifySerializer

        serializer = DocumentVerifySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # ---------------------------
        # Save DOB Proof Document
        # ---------------------------
        dob_file = data["dob_proof"]
        dob_ext = os.path.splitext(dob_file.name)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=dob_ext) as tmp:
            tmp.write(dob_file.read())
            dob_path = tmp.name

        # ---------------------------
        # Save ID Proof Document
        # ---------------------------
        id_file = data["name_gender_proof"]
        id_ext = os.path.splitext(id_file.name)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=id_ext) as tmp:
            tmp.write(id_file.read())
            id_path = tmp.name

        # ---------------------------
        # Save Address Proof Document
        # ---------------------------
        address_file = data["address_proof"]
        address_ext = os.path.splitext(address_file.name)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=address_ext) as tmp:
            tmp.write(address_file.read())
            address_path = tmp.name

        # ---------------------------
        # User details dictionary
        # ---------------------------
        user_details = {
            "first_name": data["first_name"],
            "middle_name": data.get("middle_name", ""),
            "last_name": data["last_name"],
            "gender": data["gender"],
            "dob": data["dob"],
            "address_line1": data["permanent_address_line"],
            "city": data["permanent_city"],
            "state": data["permanent_state"],
            "pincode": data["permanent_pincode"],
            "country": data["permanent_country"],
        }

        try:
            verifier = DocumentVerifier()
            result = verifier.verify_documents(
                dob_path,
                id_path,
                address_path,
                user_details
            )

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
    from ml.aadhaar_detector import is_aadhaar  

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

import cv2
import numpy as np
from ml.new_code import calc_document_quality, pdf_to_image, MAX_PIXELS

@api_view(['POST'])
def quality_score_view(request):
    import numpy as np
    import cv2
    from ml.quality_score import pdf_to_image, calc_document_quality

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Upload a file"}, status=400)

    try:
        # Read file as bytes
        data = file.read()
        
        # Determine format
        content_type = file.content_type or ""
        file_name = file.name.lower()

        if content_type == "application/pdf" or file_name.endswith(".pdf"):
            image = pdf_to_image(data)
        else:
            np_img = np.frombuffer(data, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        if image is None:
            return Response({"error": "Failed to process image/PDF. Check file integrity."}, status=400)

        # Run the advanced scoring logic
        result = calc_document_quality(image)
        return Response(result)

    except Exception as e:
        return Response({"error": f"Processing error: {str(e)}"}, status=500)

# @api_view(['POST'])
# def quality_score_view(request):
#     from ml.quality_score import process_uploaded_file, calc_scores

#     file = request.FILES.get("file")
#     if not file:
#         return Response({"error": "Upload a file"}, status=400)

#     try:
#         image = process_uploaded_file(file)
#         result = calc_scores(image)
#         return Response(result)

#     except Exception as e:
#         return Response({"error": str(e)}, status=500)
    
@api_view(['GET'])
def passport_ids_view(req):
    ids=PassportRecord.objects.values_list('id',flat=True)
    return Response({
        "count":ids.count(),
        "ids":list(ids)
    })

class PassportRecordDetailView(RetrieveAPIView):
    queryset=PassportRecord.objects.all()
    serializer_class=PassportReportSerializer
    lookup_field="id"

@api_view(['PATCH'])
def update_passport_status(req,id):
    new_status=req.data.get('status')
    if new_status not in ['REJECTED','VERIFIED','PENDING']:
        return Response ({"error":"Invalid Status"},status=400)
    record=get_object_or_404(PassportRecord,id=id)
    record.status=new_status
    record.save(update_fields=['status'])
    return Response({"id": record.id, "status": record.status})
