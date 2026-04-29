from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Budget, Transaction, Goal, Notification

# مترجم بيانات المستخدم
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# مترجم التصنيفات
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# مترجم الميزانية
class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = '__all__'

# مترجم المعاملات (المهم جداً للهيستوري)
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

# مترجم الأهداف
class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = '__all__'