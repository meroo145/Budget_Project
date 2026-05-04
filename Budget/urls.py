


from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('login/', views.login_page, name='login_url'),
    path('signup/', views.signup_page, name='signup_url'),
    path('dashboard/', views.dashboard_page, name='dashboard_url'),
]