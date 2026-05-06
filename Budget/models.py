from django.contrib.auth.models import User
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    amount      = models.FloatField()
    description = models.CharField(max_length=255, blank=True)
    date        = models.DateField()
    type        = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category    = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.type} - {self.amount} - {self.user.username}"


class Budget(models.Model):
    user             = models.ForeignKey(User, on_delete=models.CASCADE)
    amount           = models.FloatField()
    alert_percentage = models.IntegerField(default=80)
    category         = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.amount}"


class Goal(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE)
    name          = models.CharField(max_length=100)
    target_amount = models.FloatField(default=0)
    saved_amount  = models.FloatField(default=0)
    deadline      = models.DateField(null=True, blank=True)
    created_at    = models.DateField(auto_now_add=True)
    


    def __str__(self):
        return f"{self.user.username} - {self.name}"

    def percent(self):
        if self.target_amount > 0:
            return min(round((self.saved_amount / self.target_amount) * 100, 1), 100)
        return 0

    def remaining(self):
        return max(self.target_amount - self.saved_amount, 0)

    def is_completed(self):
        return self.saved_amount >= self.target_amount


class Notification(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"