from django.db import models
# import jsonfield

# Create your models here.
class User(models.Model):
    user_id=models.CharField(max_length=50,unique=True,primary_key=True)
    name=models.CharField(max_length=50)
    email=models.EmailField(max_length=50,unique=True)
    mobile_number=models.IntegerField(unique=True)

class PaymentSplit(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    debtor=models.JSONField(default=dict)
    total_payment=models.FloatField(default=0)
    expense=models.FloatField(default=0)