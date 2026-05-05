


from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('login/', views.login_page, name='login_url'),
    path('signup/', views.signup_page, name='signup_url'),
    path('dashboard/', views.dashboard_page, name='dashboard_url'),
    path('analysis/', views.analysis_page, name='analysis_url'),
    path('history/', views.history_page, name='history_url'),
    path('budgets/', views.budgets_page, name='budgets_url'),
    path('add-expense/', views.add_expense_view, name='add_expense_url'),
    path('add-income/', views.add_income_view, name='add_income_url'),
    path('create-budget/', views.create_budget_view, name='create_budget_url'),
]