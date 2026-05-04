



from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Budget.urls')), # ده بيقول لجانجو: أي حد يفتح الموقع، روح شوف الروابط اللي جوه تطبيق Budget
]