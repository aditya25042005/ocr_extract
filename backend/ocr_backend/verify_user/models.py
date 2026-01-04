# from django.db import models
# from django.utils import timezone
# from datetime import timedelta

# GENDER_CHOICES=(
#     ('M','Male'),
#     ('F','Female'),
#     ('O','Other'),
# )
# STATUS_CHOICE=(
#     ('PENDING','pending'),
#     ('VERIFIED','verified')
# )
# class PassportRecord(models.Model):
#     first_name=models.CharField(max_length=100)
#     middle_name=models.CharField(max_length=100,blank=True)
#     last_name=models.CharField(max_length=100)
#     gender=models.CharField(max_length=1,choices=GENDER_CHOICES)
#     dob=models.DateField()

#     phone=models.CharField(max_length=10)
#     email=models.EmailField()
#     #present address
#     present_address_line=models.CharField(max_length=500)
#     present_city=models.CharField(max_length=255)
#     present_state=models.CharField(max_length=100)
#     present_pincode=models.CharField(max_length=10)
#     present_country=models.CharField(max_length=100, default="India")
#     #permanent address
#     permanent_address_same_as_present=models.BooleanField(default=False)
#     permanent_address_line=models.CharField(max_length=500, blank=True)
#     permanent_city=models.CharField(max_length=100, blank=True)
#     permanent_state=models.CharField(max_length=100, blank=True)
#     permanent_pincode=models.CharField(max_length=10, blank=True)
#     permanent_country=models.CharField(max_length=100, blank=True)

#     name_gender_proof=models.FileField(upload_to="name_gender_proof/")
#     dob_proof=models.FileField(upload_to="dob_proofs/")
#     address_proof = models.FileField(upload_to="address_proofs/")

#     status=models.CharField(max_length=10,choices=STATUS_CHOICE,default='PENDING')
    
#     # raw OCR output
#     extracted_data = models.JSONField(blank=True, null=True)       
#     verification_results = models.JSONField(blank=True, null=True)

#     created_at=models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.first_name} {self.last_name} ({self.dob})"
    

# class EmailOTP(models.Model):
#     email=models.EmailField()
#     otp=models.CharField(max_length=6)
#     created_at=models.DateTimeField(auto_now_add=True)

#     def is_valid(self):
#         return timezone.now() <= self.created_at+timedelta(minutes=10)
#     def __str__(self):
#         return f"{self.email} - {self.otp}"


from django.db import models
from django.utils import timezone
from datetime import timedelta

GENDER_CHOICES=(
    ('M','Male'),
    ('F','Female'),
    ('O','Other'),
)
STATUS_CHOICE=(
    ('PENDING','pending'),
    ('VERIFIED','verified')
)
class PassportRecord(models.Model):
    first_name = models.CharField(max_length=100)
    first_name_score = models.FloatField(null=True, blank=True)

    middle_name = models.CharField(max_length=100, blank=True)
    middle_name_score = models.FloatField(null=True, blank=True)

    last_name = models.CharField(max_length=100)
    last_name_score = models.FloatField(null=True, blank=True)

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    gender_score = models.FloatField(null=True, blank=True)

    dob = models.DateField()
    dob_score = models.FloatField(null=True, blank=True)

    phone = models.CharField(max_length=10)
    phone_score = models.FloatField(null=True, blank=True)

    email = models.EmailField()
    email_score = models.FloatField(null=True, blank=True)

    # PRESENT ADDRESS (unchanged names)
    present_address_line = models.CharField(max_length=500)
    present_address_line_score = models.FloatField(null=True, blank=True)

    present_city = models.CharField(max_length=255)
    present_city_score = models.FloatField(null=True, blank=True)

    present_state = models.CharField(max_length=100)
    present_state_score = models.FloatField(null=True, blank=True)

    present_pincode = models.CharField(max_length=10)
    present_pincode_score = models.FloatField(null=True, blank=True)

    present_country = models.CharField(max_length=100, default="India")
    present_country_score = models.FloatField(null=True, blank=True)

    # PERMANENT ADDRESS
    permanent_address_same_as_present = models.BooleanField(default=False)

    permanent_address_line = models.CharField(max_length=500, blank=True)
    permanent_address_line_score = models.FloatField(null=True, blank=True)

    permanent_city = models.CharField(max_length=100, blank=True)
    permanent_city_score = models.FloatField(null=True, blank=True)

    permanent_state = models.CharField(max_length=100, blank=True)
    permanent_state_score = models.FloatField(null=True, blank=True)

    permanent_pincode = models.CharField(max_length=10, blank=True)
    permanent_pincode_score = models.FloatField(null=True, blank=True)

    permanent_country = models.CharField(max_length=100, blank=True)
    permanent_country_score = models.FloatField(null=True, blank=True)

    name_gender_proof = models.FileField(upload_to="name_gender_proof/")
    dob_proof = models.FileField(upload_to="dob_proofs/")
    address_proof = models.FileField(upload_to="address_proofs/")

    status = models.CharField(max_length=10, choices=STATUS_CHOICE, default="PENDING")

    extracted_data = models.JSONField(blank=True, null=True)
    verification_results = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() <= self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp}"
