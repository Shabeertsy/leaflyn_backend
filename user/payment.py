# payments/views.py
import razorpay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction
from .models import Order, Payment, Transaction
import hmac
import hashlib
import json



# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateRazorpayOrder(APIView):
    def post(self, request):
        order_id = request.data.get('order_id')  # Order ID from your Order model
        try:
            with transaction.atomic():  # Wrap operations in an atomic block
                order = Order.objects.select_for_update().get(id=order_id)  # Lock the order row
                if order.payment and order.payment.status == 'completed':
                    return Response({"error": "Payment already completed"}, status=status.HTTP_400_BAD_REQUEST)

                # Calculate total amount (in paisa for Razorpay)
                amount = int(order.total_amount * 100)  # Convert to paisa

                # Create Razorpay order
                razorpay_order = razorpay_client.order.create({
                    "amount": amount,
                    "currency": "INR",
                    "payment_capture": "1"  # Auto-capture payment
                })

                # Create Payment instance
                payment = Payment.objects.create(
                    order=order,
                    amount=order.total_amount,
                    method='card',  # Adjust based on frontend logic
                    status='pending',
                    transaction_id=razorpay_order['id']
                )

                return Response({
                    "razorpay_order_id": razorpay_order['id'],
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                    "amount": amount,
                    "currency": "INR",
                    "order_id": order.id
                }, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPayment(APIView):
    def post(self, request):
        data = request.data
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        try:
            # Verify the payment signature
            generated_signature = hmac.new(
                bytes(settings.RAZORPAY_KEY_SECRET, 'utf-8'),
                bytes(f"{razorpay_order_id}|{razorpay_payment_id}", 'utf-8'),
                hashlib.sha256
            ).hexdigest()

            if generated_signature != razorpay_signature:
                return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():  # Wrap database operations in an atomic block
                # Lock the payment and related order
                payment = Payment.objects.select_for_update().get(transaction_id=razorpay_order_id)
                order = payment.order

                # Update payment status
                payment.status = 'completed'
                payment.transaction_id = razorpay_payment_id
                payment.save()

                # Create transaction record
                Transaction.objects.create(
                    payment=payment,
                    transaction_id=razorpay_payment_id,
                    amount=payment.amount,
                    status='success',
                    gateway_response=json.dumps(data)
                )

                # Update order status
                order.status = 'processing'  # Or any status you want
                order.save()

                return Response({"status": "Payment verified successfully"}, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# payments/views.py
class RazorpayWebhook(APIView):
    def post(self, request):
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET  # Add to .env
        signature = request.headers.get('X-Razorpay-Signature')
        body = request.body.decode('utf-8')

        # Verify webhook signature
        generated_signature = hmac.new(
            bytes(webhook_secret, 'utf-8'),
            bytes(body, 'utf-8'),
            hashlib.sha256
        ).hexdigest()

        if signature != generated_signature:
            return Response({"error": "Invalid webhook signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():  # Wrap webhook processing in an atomic block
                event = request.data.get('event')
                if event == 'payment.captured':
                    payment_id = request.data['payload']['payment']['entity']['id']
                    payment = Payment.objects.select_for_update().get(transaction_id=payment_id)
                    payment.status = 'completed'
                    payment.save()

                    # Create transaction record
                    Transaction.objects.create(
                        payment=payment,
                        transaction_id=payment_id,
                        amount=payment.amount,
                        status='success',
                        gateway_response=json.dumps(request.data)
                    )

                    # Update order status
                    payment.order.status = 'processing'
                    payment.order.save()

                return Response({"status": "Webhook processed"}, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# loging for deploayment server
# logger = logging.getLogger(__name__)

# class VerifyPayment(APIView):
#     def post(self, request):
#         try:
#             # ... existing code ...
#             with transaction.atomic():
#                 # ... existing code ...
#                 logger.info(f"Payment verified for order {order.id}")
#             # ... existing code ...
#         except Exception as e:
#             logger.error(f"Payment verification failed: {str(e)}")
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)