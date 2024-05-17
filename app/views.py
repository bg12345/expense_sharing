from rest_framework.decorators import api_view
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from .models import User, PaymentSplit
from .serializers import UserSerializer
import sys

@api_view(["POST"])
def register(request):
    if request.method=="POST":
        try:
            data=JSONParser().parse(request)
            last_user=User.objects.order_by("-user_id").first()
            data["user_id"]=f"u{int(last_user.user_id.replace('u',''))+1}" if last_user else "u1"
            user_serializer=UserSerializer(data=data)
            if user_serializer.is_valid():
                user_serializer.save()
                if PaymentSplit.objects.exists():
                    for payment in PaymentSplit.objects.all():
                        payment.user_owes.update({data["user_id"]:0})
                        payment.save()
                user_owes={f"u{i}":0 for i in range(1,int(data["user_id"].replace("u","")))}
                payment=PaymentSplit(user=user_serializer.instance,user_owes=user_owes)
                payment.save()
                return JsonResponse({"message": "User Created Successfully","user_id":data["user_id"]}, status=status.HTTP_201_CREATED)
            return JsonResponse({"message": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def split_payment(request):
    if request.method=="POST":
        try:
            data=JSONParser().parse(request)
            payment=PaymentSplit.objects.filter(user_id=data["user_id"]).first()
            if payment:
                user_owes=payment.user_owes
                if data["expense"].lower()=="equal":
                    for user_id in data["users"]:
                        if user_id in user_owes:
                            user_owes[user_id]=round(user_owes[user_id]+data["payment"]/(len(data["users"])+1),2)
                        else:
                            return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                elif data["expense"].lower()=="exact":
                    if data["payment"]==sum(data["users"].values()):
                        for user_id,share in data["users"].items():
                            if user_id in user_owes:
                                user_owes[user_id]=round(user_owes[user_id]+share,2)
                            else:
                                return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return JsonResponse({"message": "Sum of shares among users dosn't match Payment"}, status=status.HTTP_400_BAD_REQUEST)
                elif data["expense"].lower()=="percent":
                    if sum(data["users"].values())==100:
                        data["users"].pop(data["user_id"])
                        for user_id,percent in data["users"].items():
                            if user_id in user_owes:
                                user_owes[user_id]=round(user_owes[user_id]+data["payment"]*percent/100,2)
                            else:
                                return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return JsonResponse({"message": "Sum of percentage share is not equal to 100"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return JsonResponse({"message": "Invalid Expense Value"}, status=status.HTTP_400_BAD_REQUEST)
                for other_user in PaymentSplit.objects.exclude(user_id=data["user_id"]):
                    if other_user.user_owes[data["user_id"]]!=0:
                        if user_owes[other_user.user_id]<=other_user.user_owes[data["user_id"]]:
                            other_user.user_owes[data["user_id"]]=other_user.user_owes[data["user_id"]]-user_owes[other_user.user_id]
                            user_owes[other_user.user_id]=0
                        else:
                            user_owes[other_user.user_id]=user_owes[other_user.user_id]-other_user.user_owes[data["user_id"]]
                            other_user.user_owes[data["user_id"]]=0
                        other_user.save()
                payment.user_owes.update(user_owes)
                payment.save()
                return JsonResponse({"message": "Payment Split Successfull"}, status=status.HTTP_200_OK)
            return JsonResponse({"message": "User dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(["POST"])
# def expense(request):
#     if request.method=="POST":
#         try:
#             data=JSONParser().parse(request)

#         except Exception as e:
#             print(sys.exc_info()[-1].tb_lineno,e)
#             return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def balance(request):
    if request.method=="GET":
        try:
            data={"balance":{}}
            for user in PaymentSplit.objects.all():
                user_balance={other_user.user_id:other_user.user_owes[user.user_id] for other_user in PaymentSplit.objects.exclude(user_id=user.user_id) 
                            if other_user.user_owes[user.user_id]!=0}
                if user_balance:
                    data["balance"][user.user_id]=user_balance
            return JsonResponse(data,status=status.HTTP_200_OK)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)