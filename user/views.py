from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination


from .models import Notification, Order, Product, ProductVariant, CareGuide, Categories, ShippingAddress, Cart, CartItem, Wishlist
from .serializers import *

from dashboard.models import ContactUs, TermsCondition,CustomAd


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request): 
        try:
            categories = Categories.objects.filter(active_status=True).order_by('-id')
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductCollectionListAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            products = ProductVariant.objects.filter(active_status=True)
            featured_products = products.filter(is_featured_collection=True)
            bestseller_products = products.filter(is_bestseller=True)   
            featured_serializer = ProductVariantSerializer(featured_products, many=True)
            bestseller_serializer = ProductVariantSerializer(bestseller_products, many=True)

            response_data = {
                "featured_products": featured_serializer.data,
                "bestseller_products": bestseller_serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            products = ProductVariant.objects.filter(active_status=True).order_by('-id')

            sizes = request.query_params.getlist('size')
            category_id = request.query_params.get('category_id')
            search_query = request.query_params.get('q', None)

            # Apply search filtering
            if search_query:
                products = products.filter(
                    Q(variant__icontains=search_query) |
                    Q(product__name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )

            if sizes:
                products = products.filter(size__in=sizes)
            if category_id:
                products = products.filter(product__category_id=category_id)

            if not products.exists():
                return Response({"error": "No products found"}, status=status.HTTP_404_NOT_FOUND)

            # Apply pagination
            paginator = CustomPageNumberPagination()
            paginated_products = paginator.paginate_queryset(products, request)

            if paginated_products is not None:
                serializer = ProductVariantSerializer(paginated_products, many=True)
                return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductVariantSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SimilarProductListAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            uuid = request.query_params.get('uuid')
            if not uuid:
                return Response({"error": "No uuid(s) provided"}, status=status.HTTP_400_BAD_REQUEST)

            product_variants = ProductVariant.objects.filter(uuid=uuid)
            if not product_variants.exists():
                return Response({"error": "Product(s) not found"}, status=status.HTTP_404_NOT_FOUND)

            similar_products = ProductVariant.objects.filter(

                product__category_id=product_variants.first().product.category_id
            ).exclude(uuid=uuid)[:6]
            serializer = ProductVariantSerializer(similar_products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductSingleAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            uuids = request.query_params.getlist('uuid')
            if not uuids:
                return Response({"error": "No uuid(s) provided"}, status=status.HTTP_400_BAD_REQUEST)

            product_variants = ProductVariant.objects.filter(uuid__in=uuids)
            if not product_variants.exists():
                return Response({"error": "Product(s) not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ProductVariantSerializer(product_variants, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



## contact us api
class CompanyContactAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            company_contact = CompanyContact.objects.first()
            serializer = CompanyContactSerializer(company_contact)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContactUsAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            serializer = ContactUsSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)  



class TermsConditionAPIView(APIView):   
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            terms = TermsCondition.objects.all()
            serializer = TermsConditionSerializer(terms, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class CustomAdListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            ads = CustomAd.objects.filter(active_status=True)
            ads = [ad for ad in ads if ad.is_currently_active()]

            ads.sort(key=lambda ad: (-(ad.priority or 0), -(ad.start_date.timestamp() if ad.start_date else 0), -ad.created_at.timestamp()))
            serializer = CustomAdSerializer(ads, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



## address management
class ListAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            addresses = ShippingAddress.objects.filter(user=request.user)
            serializer = AddressSerializer(addresses, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AddressAddAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            serializer = AddressSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)  


class AddressUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, uuid):
        try:
            address = ShippingAddress.objects.get(uuid=uuid,user=request.user)
            serializer = AddressSerializer(address, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SetDefaultAddressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid):
        try:
            address = ShippingAddress.objects.get(uuid=uuid, user=request.user)
            ShippingAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.is_default = True
            address.save(update_fields=["is_default"])
            serializer = AddressSerializer(address)
            return Response({"message": "Default address set successfully.", "address": serializer.data}, status=status.HTTP_200_OK)
        except ShippingAddress.DoesNotExist:
            return Response({"error": "Address not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class AddressDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def delete(self, request, uuid):
        try:
            address = ShippingAddress.objects.get(uuid=uuid,user=request.user)
            address.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



## Service Management
class ListServiceCategoryAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            categories = ServiceCategory.objects.filter(active_status=True)
            serializer = ServiceCategorySerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ListServiceAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            services = Service.objects.filter(active_status=True)
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


## Cart Management
class CartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            variant_uuid = request.data.get('variant_uuid')
            quantity = int(request.data.get('quantity', 1))

            if not variant_uuid:
                return Response({"error": "Variant UUID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                variant = ProductVariant.objects.get(uuid=variant_uuid)
            except ProductVariant.DoesNotExist:
                return Response({"error": "Product Variant not found"}, status=status.HTTP_404_NOT_FOUND)

            cart, created = Cart.objects.get_or_create(user=request.user)
            
            cart_item, item_created = CartItem.objects.get_or_create(cart=cart, variant=variant)
            
            if not item_created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            
            cart_item.save()

            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, uuid):
        try:
            cart = Cart.objects.get(user=request.user)
            try:
                # Assuming uuid passed is the CartItem UUID.
                cart_item = CartItem.objects.get(uuid=uuid, cart=cart)
                cart_item.delete()
                
                # Return updated cart
                serializer = CartSerializer(cart)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except CartItem.DoesNotExist:
                 return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        except Cart.DoesNotExist:
            return Response({"error": "Cart not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UpdateCartItemAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, uuid):
        try:
            quantity = int(request.data.get('quantity'))
            if quantity < 1:
                 return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

            cart_item = CartItem.objects.get(uuid=uuid, cart__user=request.user)
            cart_item.quantity = quantity
            cart_item.save()

            cart = cart_item.cart
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


## Wishlist Management
class WishlistAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wishlist_items = Wishlist.objects.filter(user=request.user)
            serializer = WishlistSerializer(wishlist_items, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            variant_uuid = request.data.get('variant_uuid')
            if not variant_uuid:
                return Response({"error": "Variant UUID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                variant = ProductVariant.objects.get(uuid=variant_uuid)
            except ProductVariant.DoesNotExist:
                return Response({"error": "Product Variant not found"}, status=status.HTTP_404_NOT_FOUND)

            wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, variant=variant)
            
            if created:
                message = "Added to wishlist"
                status_code = status.HTTP_201_CREATED
            else:
                message = "Already in wishlist"
                status_code = status.HTTP_200_OK

            return Response({"message": message}, status=status_code)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            variant_uuid = request.data.get('variant_uuid')
            if not variant_uuid:
                 return Response({"error": "Variant UUID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            deleted_count, _ = Wishlist.objects.filter(user=request.user, variant__uuid=variant_uuid).delete()
            
            if deleted_count > 0:
                return Response({"message": "Removed from wishlist"}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"error": "Item not found in wishlist"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class CreateCashOnDeliveryOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = request.user
            
            # 1 Validate shipping address
            shipping_address_id = request.data.get('shipping_address_id')
            if not shipping_address_id:
                return Response(
                    {'error': 'Shipping address is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                shipping_address = ShippingAddress.objects.get(
                    uuid=shipping_address_id,
                    user=profile
                )
            except ShippingAddress.DoesNotExist:
                return Response(
                    {'error': 'Shipping address not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 2️ Get user cart
            try:
                cart = profile.cart
            except Cart.DoesNotExist:
                return Response(
                    {'error': 'Cart not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            cart_items = cart.items.all()
            if not cart_items.exists():
                return Response(
                    {'error': 'Cart is empty.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3️ Create Order
            order = Order.objects.create(
                user=profile,
                shipping_address=shipping_address,
                status="pending",
                coupon=cart.coupon,
                coupon_offer=cart.coupon.offer if cart.coupon else 0,
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    variant=item.variant,
                    quantity=item.quantity,
                    price=item.variant.discounted_price()
                )

            order.save()  # triggers calculate_total() automatically
            
            cart.items.all().delete()
            cart.coupon = None
            cart.save()

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# My Orders 
class MyOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user
            orders = Order.objects.filter(user=profile).order_by('-created_at')
            paginator = CustomPageNumberPagination()
            paginated_orders = paginator.paginate_queryset(orders, request)
            from .serializers import OrderSerializer  # If not already imported

            if paginated_orders is not None:
                serializer = OrderSerializer(paginated_orders, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



## Notification apis
class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_profile = request.user
            notifications = Notification.objects.filter(user=user_profile).order_by('-created_at')
            paginator = CustomPageNumberPagination()
            page = paginator.paginate_queryset(notifications, request)
            from .serializers import NotificationSerializer

            if page is not None:
                serializer = NotificationSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = NotificationSerializer(notifications, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NotificationMarkAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            user_profile = request.user
            notification = Notification.objects.get(pk=pk, user=user_profile)
            notification.mark_as_read()
            from .serializers import NotificationSerializer
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NotificationMarkAllAsReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_profile = request.user
            notifications = Notification.objects.filter(user=user_profile, is_read=False)
            count = notifications.update(is_read=True, read_at=timezone.now())
            return Response({"message": f"{count} notifications marked as read."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class SyncCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Validate payload
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"error": "Invalid data format for 'items'"}, status=400)
        if not items:
            return Response({"error": "No items to sync"}, status=400)

        try:
            from .models import Cart, CartItem, ProductVariant  
        except ImportError:
            return Response({"error": "Cart, CartItem or ProductVariant models not found"}, status=500)

        cart, created = Cart.objects.get_or_create(user=user, defaults={})

        updated_variant_uuids = set()
        for item in items:
            variant_uuid = item.get("variantUuid")
            quantity = item.get("quantity")
            if not variant_uuid or not isinstance(quantity, int) or quantity < 1:
                continue 

            try:
                variant = ProductVariant.objects.get(uuid=variant_uuid)
            except ProductVariant.DoesNotExist:
                continue 

            cart_item, _ = CartItem.objects.get_or_create(cart=cart, variant=variant, defaults={'quantity': quantity})
            if cart_item.quantity != quantity:
                cart_item.quantity = quantity
                cart_item.save()
            updated_variant_uuids.add(variant_uuid)

     
        CartItem.objects.filter(cart=cart).exclude(variant__uuid__in=updated_variant_uuids).delete()

        try:
            from .serializers import CartSerializer
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ImportError:
            return Response({"success": True, "cart_id": str(cart.uuid)}, status=status.HTTP_200_OK)

