from django.urls import path
from . import views

urlpatterns = [
    path('',                            views.home_page,          name='home'),
    path('login/',                      views.login_page,          name='login_url'),
    path('signup/',                     views.signup_page,         name='signup_url'),
    path('logout/',                     views.logout_view,         name='logout_url'),
    path('dashboard/',                  views.dashboard_page,      name='dashboard_url'),
    path('profile/',                    views.profile_page,        name='profile_url'),
    path('analysis/',                   views.analysis_page,       name='analysis_url'),
    path('history/',                    views.history_page,        name='history_url'),
    path('history/export/',             views.export_csv,          name='export_csv'),
    path('history/delete/<int:pk>/',    views.delete_transaction,  name='delete_transaction'),
    path('budgets/',                    views.budgets_page,        name='budgets_url'),
    path('budgets/delete/<int:pk>/',    views.delete_budget,       name='delete_budget'),
    path('add-expense/',                views.add_expense_view,    name='add_expense_url'),
    path('add-income/',                 views.add_income_view,     name='add_income_url'),
    path('create-budget/',              views.create_budget_view,  name='create_budget_url'),
    path('goals/',                      views.goals_page,          name='goals_url'),
    path('goals/create/',               views.create_goal,         name='create_goal_url'),
    path('goals/add-savings/<int:pk>/', views.add_savings,         name='add_savings_url'),
    path('goals/delete/<int:pk>/',      views.delete_goal,         name='delete_goal_url'),
    path('history/edit/<int:pk>/',      views.edit_transaction,    name='edit_transaction'),
]