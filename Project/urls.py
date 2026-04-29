from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls), # ده عشان تدخل لصفحة إدارة ديجانجو
    path('api/', include('Budget.urls')), # ده اللي بيربط بالملف اللي فوق اللي لسه مخلصينه
]