from django.urls import path
from .views import * 

urlpatterns = [
    path('passport/create/',PassportRecordCreateView.as_view(),name='passport-create')
]