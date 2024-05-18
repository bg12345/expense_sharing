from rest_framework.decorators import api_view
from django.http.response import JsonResponse
from rest_framework.parsers import JSONParser
from rest_framework import status
from .models import User, PaymentSplit
from .serializers import UserSerializer
from django.forms.models import model_to_dict
import sys

@api_view(["POST"])
def register(request):
    if request.method=="POST":
        try:
            # Parse the JSON request data
            data=JSONParser().parse(request)
            # Get the last user to generate a new user_id
            last_user=User.objects.order_by("-user_id").first()
            # Generate a new user_id
            data["user_id"]=f"u{int(last_user.user_id.replace('u',''))+1}" if last_user else "u1"
            # Serialize the user data
            user_serializer=UserSerializer(data=data)
            # Check if the serialized data is valid
            if user_serializer.is_valid():
                # Save the new user
                user_serializer.save()
                # If there are existing PaymentSplit records, update them with the new user_id
                if PaymentSplit.objects.exists():
                    for payment in PaymentSplit.objects.all():
                        payment.debtor.update({data["user_id"]:0})
                        payment.save()
                # Create a debtor dictionary for the new PaymentSplit record
                debtor={f"u{i}":0 for i in range(1,int(data["user_id"].replace("u","")))}
                # Create a new PaymentSplit record for the new user
                payment=PaymentSplit(user=user_serializer.instance,debtor=debtor)
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
            # Parse the JSON request data
            data=JSONParser().parse(request)
            # Find the PaymentSplit record for the given user_id
            payment=PaymentSplit.objects.filter(user_id=data["user_id"]).first()
            # Check if the payment record exists
            if payment:
                debtor=payment.debtor
                 # Check for threshold of participant users
                if len(data["users"])>1000:
                    return JsonResponse({"message": "No. of participant users exceed given threshold i.e 1000"}, status=status.HTTP_400_BAD_REQUEST)
                # Check for payment threshold
                if data["payment"]>10000000:
                    return JsonResponse({"message": "Payment exceed given threshold i.e INR 1,00,00,000"}, status=status.HTTP_400_BAD_REQUEST)
                # Handle expense type for "equal","exact" and "percent"
                if data["expense"].lower()=="equal":
                    expense=round(data["payment"]/(len(data["users"])+1),2)
                    for user_id in data["users"]:
                        if user_id in debtor:
                            debtor[user_id]=round(debtor[user_id]+data["payment"]/(len(data["users"])+1),2)
                        else:
                            return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                elif data["expense"].lower()=="exact":
                    if data["payment"]==sum(data["users"].values()):
                        expense=0
                        for user_id,share in data["users"].items():
                            if user_id in debtor:
                                debtor[user_id]=round(debtor[user_id]+share,2)
                            else:
                                return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return JsonResponse({"message": "Sum of shares among users dosn't match Payment"}, status=status.HTTP_400_BAD_REQUEST)
                elif data["expense"].lower()=="percent":
                    if sum(data["users"].values())==100:
                        expense=round(data["payment"]*data["users"][data["user_id"]]/100,2)
                        data["users"].pop(data["user_id"])
                        for user_id,percent in data["users"].items():
                            if user_id in debtor:
                                debtor[user_id]=round(debtor[user_id]+data["payment"]*percent/100,2)
                            else:
                                return JsonResponse({"message": f"{user_id} dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # Handle invalid expense type
                        return JsonResponse({"message": "Sum of percentage share is not equal to 100"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return JsonResponse({"message": "Invalid Expense Value"}, status=status.HTTP_400_BAD_REQUEST)
                # Adjust balances between users
                for other_user in PaymentSplit.objects.exclude(user_id=data["user_id"]):
                    if other_user.debtor[data["user_id"]]!=0:
                        if debtor[other_user.user_id]<=other_user.debtor[data["user_id"]]:
                            other_user.debtor[data["user_id"]]=other_user.debtor[data["user_id"]]-debtor[other_user.user_id]
                            debtor[other_user.user_id]=0
                        else:
                            debtor[other_user.user_id]=debtor[other_user.user_id]-other_user.debtor[data["user_id"]]
                            other_user.debtor[data["user_id"]]=0
                        other_user.save()
                # Update the payment record with new payment and expense
                payment.total_payment=round(payment.total_payment+data["payment"],2)
                payment.expense=round(payment.expense+expense,2)
                payment.debtor.update(debtor)
                payment.save()
                return JsonResponse({"message": "Payment Split Successfull"}, status=status.HTTP_200_OK)
            return JsonResponse({"message": "User dosen't exist"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def expense(request):
    if request.method=="GET":
        try:
            # Retrieve the user_id from the GET request parameters
            user_id=request.GET.get("user_id")
            # Find the PaymentSplit record for the given user_id
            payment=PaymentSplit.objects.filter(user_id=user_id).first()
            # Check if the payment record exists
            if payment:
                # Convert the payment model instance to a dictionary
                payment=model_to_dict(payment)
                # Remove debtor entries where the value is 0
                payment["debtor"]={k:v for k,v in payment["debtor"].items() if v!=0}
                payment.pop("id")
                return JsonResponse(payment,status=status.HTTP_200_OK)
            return JsonResponse({"message": "User dosen't exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def balance(request):
    if request.method=="GET":
        try:
            # Initialize an empty dictionary to hold the balance information
            data={"balance":{}}
            # Iterate over all PaymentSplit records
            for user in PaymentSplit.objects.all():
                # Create a dictionary to hold the balances for the current user
                user_balance={other_user.user_id:other_user.debtor[user.user_id] for other_user in PaymentSplit.objects.exclude(user_id=user.user_id) 
                            if other_user.debtor[user.user_id]!=0}
                # If the user has non-zero balances with other users, add it to the data
                if user_balance:
                    data["balance"][user.user_id]=user_balance
            return JsonResponse(data,status=status.HTTP_200_OK)
        except Exception as e:
            print(sys.exc_info()[-1].tb_lineno,e)
            return JsonResponse({"message": "Something went wrong"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)