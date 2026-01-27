
from rest_framework import status, exceptions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import exception_handler
from rest_framework import status as drf_status
from find_worker_config.model_choice import PaymentCurrencyType, PaymentTransactionType, ServiceChargeType
from task.models import PaymentTransaction, AdminWallet
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

class UpdateModelViewSet(ModelViewSet):
    delete_message = "Object Successfully Deleted!"
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.perform_retrieve(serializer)
    
    def perform_retrieve(self, serializer):
        return Response(
            {
                'status': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK
        )
    
    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            return Response(
                {
                    'status': True,
                    'count': len(response.data),
                    'data': response.data
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'messgae': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    'status': True,
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except exceptions.ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except exceptions.PermissionDenied as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            serializer = self.get_serializer(object, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(
                {
                    'status': True,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except exceptions.ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'message': self.delete_message,
            }, status=status.HTTP_200_OK
        )

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        message = ""
        if isinstance(response.data, dict):
            message = response.data.get("detail") or next(iter(response.data.values()), [""])[0]
        else:
            message = str(response.data)

        custom_response = {
            "status": False,
            "message": message
        }
        response.data = custom_response
    else:
        return Response(
            {"status": False, "message": str(exc)},
            status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return response

def log_activity(*, user, action: str, entity_type: str, entity_id=None, metadata=None, request=None):
    from account.models import ActivityLog
    ActivityLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
        ip_address=request.META.get("REMOTE_ADDR") if request else None
    )


class PaymentTransactionModule:
    def __init__(self, user, amount, reference_object, type, action, payment_information: dict={}, reference=None, currency=None, service_charge: dict={}):
        self.user = user
        self.amount = amount
        self.payment_information = payment_information
        self.reference_object = reference_object
        self.type = type
        self.action = action
        self.reference = reference
        self.currency = currency or PaymentCurrencyType.CA
        self.service_charge = service_charge
    
    def get_wallet(self):
        wallet, _ = AdminWallet.objects.get_or_create()
        return wallet
    
    def get_service_charge_amount(self, amount):
        charge_type = self.service_charge.get("type")
        charge_number = self.service_charge.get("number")
        if charge_type == ServiceChargeType.FLAT:
            charge = charge_number
        elif charge_type == ServiceChargeType.PERCENTAGE:
            charge = (amount * charge_number) / 100
        else:
            charge = (amount * 10) / 100
        payable_amount = amount-charge
        return charge, payable_amount
    
    def update_wallet(self, transaction):
        wallet = self.get_wallet()
        amount = transaction.amount
        if self.type == PaymentTransactionType.CREDIT:
            wallet.payment_balance += amount
        elif self.type == PaymentTransactionType.HOLD:
            wallet.payment_balance -= amount
            wallet.hold_balance += amount
        elif self.type == PaymentTransactionType.DEBIT:
            charge_amount, payable_amount = self.get_service_charge_amount(amount)
            transaction.amount = payable_amount
            transaction.save(update_fields=["amount"])
            wallet.hold_balance -= amount
            wallet.total_withdraw += payable_amount
            wallet.current_balance += charge_amount
        wallet.save(update_fields=[
            "payment_balance",
            "hold_balance",
            "total_withdraw",
            "current_balance",
        ])
        return True

    def payment_transaction(self):
        entity_type = ContentType.objects.get_for_model(self.reference_object)
        with transaction.atomic():
            payment_transaction = PaymentTransaction.objects.create(
                user=self.user,
                amount=self.amount,
                payment_information=self.payment_information or {},
                entity_type=entity_type,
                entity_id=self.reference_object.id,
                type=self.type,
                action=self.action,
                reference=self.reference,
                currency=self.currency or PaymentCurrencyType.CA
            )
            self.update_wallet(payment_transaction)
            return True
        raise Exception("Payment Transaction not update.")


