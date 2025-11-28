import os
import time
import uuid
import json
import logging
from decimal import Decimal
from typing import Dict

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from payment.gateway_manager import (
    PaymentGatewayManager,
    GatewayClientFactory,
    PaymentGatewayLog
)
from .models import Payment, Transaction, PaymentLog, PaymentGateway
from .exceptions import PaymentError, InvalidPaymentError
from .utils import validate_amount, sanitize_user_input, get_client_ip
from user.models import Order, OrderItem, ProductVariant, ShippingAddress

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)



class PaymentManager:
    @staticmethod
    def create_payment(user, amount: Decimal, paid_for=None, order=None, **kwargs) -> Payment:
        with transaction.atomic():
            payment_data = {
                'user': user,
                'amount': amount,
                'status': 'initiated',
                'merchant_transaction_id': str(uuid.uuid4()),
                'payment_method': kwargs.get('payment_method', 'phonepe'),
                'initiated_at': timezone.now(),
                'ip_address': kwargs.get('ip_address'),
                'user_agent': kwargs.get('user_agent', '')[:500],
            }

            if paid_for:
                payment_data['content_type'] = ContentType.objects.get_for_model(paid_for)
                payment_data['object_id'] = paid_for.pk

            payment_data.update({
                'customer_phone': kwargs.get('customer_phone', ''),
                'customer_email': kwargs.get('customer_email', ''),
                'customer_name': kwargs.get('customer_name', ''),
                'payment_metadata': kwargs.get('metadata', {}),
            })

            if order is not None:
                payment_data['order'] = order

            payment = Payment.objects.create(**payment_data)

            PaymentLog.log_payment_event(
                payment=payment,
                action='payment_initiated',
                details={
                    'amount': str(amount),
                    'method': payment_data['payment_method'],
                    'sdk_version': 'v2',
                    'description': kwargs.get('description', '')
                },
                user=user,
                ip_address=kwargs.get('ip_address')
            )
            return payment

    @staticmethod
    def create_transaction(payment: Payment, **kwargs) -> Transaction:
        with transaction.atomic():
            transaction_obj = Transaction.objects.create(
                payment=payment,
                order_id=getattr(payment, "merchant_transaction_id", ""),
                transaction_id=kwargs.get('transaction_id', ''),
                payment_method=payment.payment_method,
                amount=payment.amount,
                status=kwargs.get('status', 'pending'),
                gateway_response=kwargs.get('gateway_response', {}),
                ip_address=kwargs.get('ip_address'),
            )
            PaymentLog.log_payment_event(
                payment=payment,
                action='transaction_created',
                details={
                    'transaction_db_id': transaction_obj.id,
                    'transaction_status': transaction_obj.status,
                    'sdk_used': True
                },
                user=payment.user,
                ip_address=kwargs.get('ip_address')
            )
            return transaction_obj

    @staticmethod
    def update_payment_status(payment: Payment, status: str, gateway_data: Dict = None, phonepe_transaction_id: str = None) -> Payment:
        with transaction.atomic():
            old_status = payment.status
            payment.status = status

            if status == 'completed' and not payment.completed_at:
                payment.completed_at = timezone.now()
            elif status == 'failed' and not payment.failed_at:
                payment.failed_at = timezone.now()

            payment.save()
            if payment.transactions.exists():
                latest_transaction = payment.transactions.latest('created_at')
                latest_transaction.status = status
                if gateway_data:
                    latest_transaction.payment_mode = gateway_data.get('payment_mode', 'no data')
                    latest_transaction.gateway_response = gateway_data
                    if hasattr(latest_transaction, "update_from_phonepe_response"):
                        latest_transaction.update_from_phonepe_response(gateway_data)
                    if latest_transaction.status != status:
                        latest_transaction.status = status
                if phonepe_transaction_id:
                    latest_transaction.transaction_id = phonepe_transaction_id
                latest_transaction.save()
            else:
                PaymentManager.create_transaction(
                    payment=payment,
                    transaction_id=phonepe_transaction_id or '',
                    gateway_response=gateway_data or {},
                    payment_mode=gateway_data.get('payment_mode', 'no data') if gateway_data else None,
                    status=status
                )

            # Update related Order status if payment relates to an order
            order = getattr(payment, "order", None)
            if order:
                if status == "completed":
                    order.status = "processing"
                elif status == "failed":
                    order.status = "cancelled"
                order.save()

            log_details = {
                'old_status': old_status,
                'new_status': status,
                'gateway_data_received': bool(gateway_data),
                'phonepe_transaction_id': phonepe_transaction_id
            }
            if gateway_data:
                # Make gateway_data loggable.
                serializable_gateway_data = {}
                for key, value in gateway_data.items():
                    try:
                        json.dumps(value)
                        serializable_gateway_data[key] = value
                    except (TypeError, ValueError):
                        serializable_gateway_data[key] = str(value)
                log_details['gateway_data_sample'] = serializable_gateway_data

            PaymentLog.log_payment_event(
                payment=payment,
                action='status_updated',
                details=log_details,
                user=payment.user
            )
            return payment


class ListPaymentGatewaysView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gateways = PaymentGatewayManager.get_active_gateways()

        gateway_data = []
        for gateway in gateways:
            gateway_data.append({
                'id': gateway.id,
                'name': gateway.name,
                'display_name': gateway.display_name,
                'description': gateway.description,
                'logo': gateway.logo.url if gateway.logo else None,
                'is_default': gateway.is_default,
                'min_amount': str(gateway.min_amount),
                'max_amount': str(gateway.max_amount) if gateway.max_amount else None,
                'features': {
                    'supports_refund': gateway.supports_refund,
                    'supports_upi': gateway.supports_upi,
                    'supports_cards': gateway.supports_cards,
                    'supports_netbanking': gateway.supports_netbanking,
                    'supports_wallets': gateway.supports_wallets,
                },
                'transaction_fee': {
                    'percentage': str(gateway.transaction_fee_percentage),
                    'fixed': str(gateway.transaction_fee_fixed),
                }
            })

        return Response({
            'gateways': gateway_data,
            'default_gateway': next(
                (g['name'] for g in gateway_data if g['is_default']),
                None
            )
        })


@method_decorator(csrf_exempt, name='dispatch')
class InitiatePaymentView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            data = request.data if hasattr(request, "data") else request.POST
            gateway_name = data.get('gateway')
            order_id = data.get("order_id")
            amount_str = sanitize_user_input(data.get("amount", ""))
            description = sanitize_user_input(data.get("description", ""))
            customer_phone = sanitize_user_input(data.get("phone", ""))

            paid_for_obj = None
            order_obj = None

            if order_id:
                try:
                    order_obj = Order.objects.get(id=order_id, user=request.user)
                    amount = order_obj.total_amount
                    paid_for_obj = order_obj
                except Order.DoesNotExist:
                    return Response(
                        {"error": "Order not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                try:
                    amount = validate_amount(amount_str)
                except Exception as e:
                    return Response(
                        {"error": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if not amount or amount <= 0:
                return Response(
                    {"error": "A positive amount is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                gateway = PaymentGatewayManager.get_suitable_gateway(amount, gateway_name)
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cache_key = f"payment_initiation_{request.user.id}"
            if cache.get(cache_key):
                return Response(
                    {"error": "Please wait before initiating another payment."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            cache.set(cache_key, True, timeout=5)

            payment = PaymentManager.create_payment(
                user=request.user,
                amount=amount,
                paid_for=paid_for_obj,
                order=order_obj,
                customer_phone=customer_phone,
                customer_email=request.user.email,
                customer_name=request.user.get_full_name(),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'description': description},
                description=description,
                payment_method=gateway.name
            )

            payment.gateway = gateway
            payment.payment_method = gateway.name
            payment.save()

            PaymentManager.create_transaction(
                payment=payment,
                ip_address=get_client_ip(request),
            )

            try:
                gateway_client = GatewayClientFactory.get_client(gateway)

                frontend_callback_url = data.get("redirect_url") or request.build_absolute_uri(
                    f"/pay/status/{payment.merchant_transaction_id}/"
                )

                result = gateway_client.initiate_payment(payment, frontend_callback_url)
                if result.get('success'):
                    PaymentManager.update_payment_status(
                        payment,
                        'pending',
                        gateway_data=None,
                        phonepe_transaction_id=None
                    )
                    response_data = {
                        "payment_id": payment.id,
                        "merchant_transaction_id": payment.merchant_transaction_id,
                        "status": "initiated",
                        "gateway": {
                            "name": gateway.name,
                            "display_name": gateway.display_name
                        }
                    }
                    # Gateway-specific fields
                    if gateway.name == 'phonepe':
                        response_data['redirect_url'] = result.get('redirect_url')
                    elif gateway.name == 'razorpay':
                        response_data['razorpay_data'] = {
                            'order_id': result.get('order_id'),
                            'key_id': result.get('key_id'),
                            'amount': result.get('amount'),
                            'currency': result.get('currency')
                        }
                    elif gateway.name == 'stripe':
                        response_data['session_id'] = result.get('session_id')
                        response_data['redirect_url'] = result.get('redirect_url')
                    logger.info(f"Payment initiated via {gateway.name}: {payment.merchant_transaction_id}")
                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    return Response(
                        {"error": "Payment initiation failed"},
                        status=status.HTTP_502_BAD_GATEWAY
                    )
            except Exception as gateway_error:
                logger.error(f"Gateway {gateway.name} error: {gateway_error}")
                PaymentGatewayManager.log_gateway_action(
                    gateway=gateway,
                    action='payment_initiation_error',
                    status='failed',
                    error_message=str(gateway_error),
                    payment=payment,
                    ip_address=get_client_ip(request)
                )
                return Response(
                    {"error": f"Payment gateway error: {str(gateway_error)}"},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        except Exception as e:
            logger.exception("Unexpected error during payment initiation")
            return Response(
                {"error": "An unexpected error occurred. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdatedPaymentStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, merchant_transaction_id=None, *args, **kwargs):
        return self.handle_status_check(request, merchant_transaction_id)

    def post(self, request, merchant_transaction_id=None, *args, **kwargs):
        if not merchant_transaction_id:
            merchant_transaction_id = request.data.get("merchantTransactionId")
        return self.handle_status_check(request, merchant_transaction_id)

    def handle_status_check(self, request, merchant_transaction_id):
        try:
            if not merchant_transaction_id:
                return Response(
                    {"error": "Invalid payment session.", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                payment = (
                    Payment.objects.select_related("user", "gateway")
                    .prefetch_related("transactions")
                    .get(merchant_transaction_id=merchant_transaction_id)
                )
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment session not found.", "status": "error"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Status refresh from gateway
            if payment.status in ["pending", "initiated"]:
                try:
                    gateway_client = GatewayClientFactory.get_client(payment.gateway)
                    status_result = gateway_client.check_status(merchant_transaction_id)
                    if status_result.get('success'):
                        gateway_status = status_result.get('status')
                        status_map = {
                            "completed": "completed",
                            "success": "completed",
                            "failed": "failed",
                            "cancelled": "failed",
                            "pending": "pending",
                            "created": "initiated",
                        }
                        new_status = status_map.get(gateway_status, payment.status)
                        if new_status != payment.status:
                            gateway_response = status_result.get('response')
                            gateway_data = {
                                'state': gateway_status,
                                'gateway_name': payment.gateway.name,
                                'raw_response': str(gateway_response)
                            }
                            PaymentManager.update_payment_status(
                                payment=payment,
                                status=new_status,
                                gateway_data=gateway_data,
                                phonepe_transaction_id=None
                            )
                            payment.refresh_from_db()
                except Exception as e:
                    logger.error(f"Gateway status check failed: {e}")
                    PaymentGatewayManager.log_gateway_action(
                        gateway=payment.gateway,
                        action="status_check_failed",
                        status='failed',
                        error_message=str(e),
                        payment=payment,
                        ip_address=get_client_ip(request)
                    )

            latest_transaction = payment.transactions.order_by("-created_at").first()
            order_obj = getattr(payment, "order", None)

            response_data = {
                "merchant_transaction_id": payment.merchant_transaction_id,
                "payment_status": payment.status,
                "amount": payment.get_display_amount(),
                "transaction_id": (
                    latest_transaction.transaction_id
                    if latest_transaction
                    else payment.merchant_transaction_id
                ),
                "gateway": {
                    "name": payment.gateway.name,
                    "display_name": payment.gateway.display_name
                } if payment.gateway else None,
                "paid_for": str(payment.paid_for) if payment.paid_for else None,
                "payment_date": str(
                    (latest_transaction.created_at
                     if latest_transaction and latest_transaction.status == "completed"
                     else payment.completed_at) or payment.created_at
                ),
                "payment_method": (
                    getattr(latest_transaction, "payment_mode", None)
                    if latest_transaction
                    else payment.payment_method
                ),
                "order": getattr(order_obj, "id", None) if order_obj else None,
                "order_status": getattr(order_obj, "status", None) if order_obj else None,
            }

            if payment.status == "completed":
                response_data["message"] = f"Payment of {payment.get_display_amount()} completed successfully!"
                return Response(response_data, status=status.HTTP_200_OK)
            elif payment.status == "failed":
                response_data["message"] = "Payment failed. Please try again or contact support."
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data["message"] = "Payment is being processed. Please wait..."
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error checking payment status")
            return Response(
                {
                    "error": "Unable to verify payment status. Please contact support.",
                    "merchant_transaction_id": merchant_transaction_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@require_http_methods(["POST"])
@csrf_exempt
def payment_gateway_webhook(request, gateway_name=None):
    """
    Generic webhook handler for all configured payment gateways.
    If 'gateway_name' is not provided as a path kwarg, try to infer from request path or content (fallback not recommended for production).
    """
    try:
        webhook_start_time = time.time()
        client_ip = get_client_ip(request)
        # Try get gateway name from function argument, fallback to 'phonepe' for legacy support
        name = gateway_name or request.GET.get('gateway') or 'phonepe'
        gateway = PaymentGatewayManager.get_gateway_by_name(name)
        if not gateway:
            logger.error(f"{name} gateway not found for webhook processing")
            return Response({"error": f"{name.title()} gateway not configured."}, status=500)

        gateway_client = GatewayClientFactory.get_client(gateway)
        result = gateway_client.process_webhook(request)
        # Optionally log audit info, timing, etc.
        return Response(result, status=200 if result.get('success') else 400)
    except Exception as e:
        logger.exception(f"Critical error processing {gateway_name or 'unknown'} gateway webhook")
        return Response({"error": "Internal server error"}, status=500)


@method_decorator([login_required, require_http_methods(["GET"])], name='dispatch')
class PaymentHistoryView(View):
    def get(self, request, *args, **kwargs):
        payments_queryset = Payment.objects.filter(
            user=request.user
        ).select_related('content_type', 'order').prefetch_related('transactions').order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter and status_filter in ['completed', 'failed', 'pending', 'initiated']:
            payments_queryset = payments_queryset.filter(status=status_filter)

        search_query = request.GET.get('search')
        if search_query:
            try:
                search_amount = Decimal(search_query)
                payments_queryset = payments_queryset.filter(amount=search_amount)
            except Exception:
                payments_queryset = payments_queryset.filter(
                    payment_metadata__description__icontains=search_query
                )

        paginator = Paginator(payments_queryset, 10)
        page = request.GET.get('page')

        try:
            payments_page = paginator.page(page)
        except PageNotAnInteger:
            payments_page = paginator.page(1)
        except EmptyPage:
            payments_page = paginator.page(paginator.num_pages)

        all_payments = Payment.objects.filter(user=request.user)
        stats = {
            'total_payments': all_payments.count(),
            'successful_payments': all_payments.filter(status='completed').count(),
            'total_amount_paid': sum(p.amount for p in all_payments.filter(status='completed')),
            'pending_payments': all_payments.filter(status__in=['pending', 'initiated']).count(),
        }

        context = {
            'payments': payments_page,
            'stats': stats,
            'current_filters': {
                'status': status_filter,
                'search': search_query,
            }
        }
        return render(request, "payment/payment_history.html", context)


@method_decorator(login_required, name='dispatch')
class PaymentDetailView(View):

    def get(self, request, merchant_transaction_id, *args, **kwargs):
        try:
            payment = get_object_or_404(
                Payment.objects.select_related('user', 'content_type', 'order')
                              .prefetch_related('transactions', 'logs'),
                merchant_transaction_id=merchant_transaction_id,
                user=request.user
            )
            order_obj = getattr(payment, "order", None)
            context = {
                'payment': payment,
                'transactions': payment.transactions.all().order_by('-created_at'),
                'recent_logs': payment.logs.all().order_by('-created_at')[:10],
                'can_retry': payment.status == 'failed',
                'payment_metadata': payment.payment_metadata,
                'order': order_obj,
            }
            return render(request, "payment/payment_detail.html", context)
        except Exception as e:
            logger.exception(f"Error displaying payment detail: {e}")
            messages.error(request, "Payment details not found.")
            return redirect('payment:history')


@method_decorator([login_required, require_http_methods(["GET"])], name='dispatch')
class PaymentDashboardView(View):

    def get(self, request, *args, **kwargs):
        user_payments = Payment.objects.filter(user=request.user)

        stats = {
            'total_payments': user_payments.count(),
            'successful_payments': user_payments.filter(status='completed').count(),
            'failed_payments': user_payments.filter(status='failed').count(),
            'pending_payments': user_payments.filter(status__in=['pending', 'initiated']).count(),
            'total_amount_paid': sum(p.amount for p in user_payments.filter(status='completed')),
            'recent_payments': user_payments.order_by('-created_at')[:5],
            'this_month_payments': user_payments.filter(
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year
            ).count(),
            'success_rate': 0,
        }

        if stats['total_payments'] > 0:
            stats['success_rate'] = round(
                (stats['successful_payments'] / stats['total_payments']) * 100, 1
            )

        context = {
            'stats': stats,
            'user': request.user,
        }
        return render(request, "payment/dashboard.html", context)


def get_payment_stats_for_admin():
    from django.db.models import Count, Sum

    stats = Payment.objects.aggregate(
        total_payments=Count('id'),
        total_amount=Sum('amount'),
        successful_payments=Count('id', filter=Q(status='completed')),
        failed_payments=Count('id', filter=Q(status='failed')),
    )
    return stats

def retry_failed_payment(payment_id: int, user) -> bool:
    try:
        payment = Payment.objects.get(id=payment_id, user=user, status='failed')
        order = getattr(payment, "order", None)
        new_payment = PaymentManager.create_payment(
            user=payment.user,
            amount=payment.amount,
            paid_for=payment.paid_for,
            order=order,
            customer_phone=payment.customer_phone,
            customer_email=payment.customer_email,
            customer_name=payment.customer_name,
            metadata=payment.payment_metadata,
            payment_method=payment.payment_method
        )
        PaymentLog.log_payment_event(
            payment=new_payment,
            action='payment_retry',
            details={'original_payment_id': payment_id},
            user=user
        )
        return True
    except Exception as e:
        logger.error(f"Failed to retry payment {payment_id}: {e}")
        return False