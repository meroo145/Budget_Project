from django.db import models
from django.contrib.auth.models import User

# 1. جدول التصنيفات
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# 2. جدول الميزانية (مربوط بالدياجرام)
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.FloatField() # double في الرسمة يعني Float هنا
    # category مربوط بجدول التصنيفات
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

# 3. جدول المعاملات
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.FloatField()
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

# 4. جدول الأهداف (الجديد من الرسمة)
class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    target_amount = models.FloatField(default=0) # ضفنا دي عشان الهدف لازم له رقم

# 5. جدول التنبيهات (الجديد من الرسمة)
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()