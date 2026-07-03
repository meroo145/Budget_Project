from django.contrib import admin
from .models import Category, Transaction, Budget, Goal, Notification, AIInsight

# Register your models here.

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(Budget)
admin.site.register(Goal)
admin.site.register(Notification)
admin.site.register(AIInsight)