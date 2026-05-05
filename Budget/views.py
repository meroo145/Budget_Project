from rest_framework import viewsets
from .models import Category, Budget, Transaction, Goal, Notification
from .serializers import CategorySerializer, BudgetSerializer, TransactionSerializer, GoalSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class BudgetViewSet(viewsets.ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer

from django.shortcuts import render

def home_page(request):
    return render(request, 'home.html')


def login_page(request):
    return render(request, 'login.html')

def signup_page(request):
    return render(request, 'sign.html')

def dashboard_page(request):
    return render(request, 'dashboard.html')

def analysis_page(request):
    return render(request, 'analysis.html') 

def history_page(request):
    return render(request, 'history.html')

def budgets_page(request):
    return render(request, 'budgets.html')

def add_expense_view(request):
    return render(request, 'add.expense.html')

def add_income_view(request):
    return render(request, 'add.income.html')

def create_budget_view(request):
    return render(request, 'create_budget.html')