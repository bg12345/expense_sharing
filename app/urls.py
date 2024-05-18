from django.urls import path
from . import views

urlpatterns=[
    path("register/",views.register, name="register"),
    path("split_payment/",views.split_payment, name="split_payment"),
    path("balance/",views.balance, name="balance"),
    path("expense/",views.expense, name="expense")
]