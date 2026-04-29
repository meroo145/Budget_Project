from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, BudgetViewSet, TransactionViewSet, GoalViewSet

# الـ Router ده هو اللي بيعمل العناوين أوتوماتيك لكل الجداول
router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'budgets', BudgetViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'goals', GoalViewSet)

urlpatterns = [
    path('', include(router.urls)),
]