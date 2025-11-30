
# ==== Python Standard Library Imports ====
from datetime  import date, timedelta
from datetime import datetime

# ==== Django Core Imports ====
from django.db               import models
from django.db.models        import Q, Count
from django.utils            import timezone
from django.utils.dateformat import format as date_format
from django.shortcuts        import get_object_or_404, redirect, render
from django.contrib          import messages
from django.contrib.auth     import authenticate, login, logout
from django.views            import View
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators      import method_decorator
from django.http                 import JsonResponse

# ==== Dashboard App Imports ====
from dashboard.forms      import (
    CategoriesForm, CouponForm, PaymentGatewayForm, ProductColorForm, ProductForm, 
    ProductVariantForm, SizeForm, CareGuideForm
)
from dashboard.excel_pdf  import download_excel_dynamic, generate_pdf_dynamic
from .mixins             import PaginationSearchMixin
from .models             import ContactUs, TermsCondition

# ==== User and Authentication App Imports ====
from user.models           import (
    Categories, Colors, CompanyContact, Coupon, Order, OrderItem, Product, 
    ProductImage, ProductVariant, Sizes, Wishlist, CareGuide
)


from authentication.models     import Profile
from authentication.permissions import *
from user.models import Wishlist
from user.models import Notification


## rest 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from user.models import Notification
from payment.models import PaymentGateway


## email imports
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from django.conf import settings    



class HomeView(AdminPermissionMixin, View):
    template_name = 'home/index.html'

    def get(self, request):
        # Trending Products calculations
        # Use Order, not OrderItem: get top 5 orders by total units sold (order.calculate_total used for revenue)
        trending_orders = (
            Order.objects
            .annotate(
                units_sold=models.Sum('items__quantity')
            )
            .order_by('-units_sold')[:5]
        )

        trending = []
        for order in trending_orders:
            # Find the "main" OrderItem (highest quantity, first by id for tie)
            order_item = order.items.order_by('-quantity', 'id').first()
            if order_item and order_item.variant and order_item.variant.product:
                trending.append({
                    'variant__product': order_item.variant.product.id,
                    'units_sold': order.units_sold,
                    'revenue': float(order.calculate_total()) if order.total_amount is not None else 0
                })

        trending_products_list = []
        trending_product_ids = [row['variant__product'] for row in trending]

        # If fewer than 5, fetch at most 5
        products_qs = Product.objects.filter(id__in=trending_product_ids)
        products_map = {p.id: p for p in products_qs}

        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        sixty_days_ago = today - timedelta(days=60)

        period_orders = OrderItem.objects.filter(order__created_at__gte=thirty_days_ago) \
            .values('variant__product') \
            .annotate(units_sold=Count('id'))
        period_map = {row['variant__product']: row['units_sold'] for row in period_orders}

        # Previous period orderitems
        prev_period_orders = OrderItem.objects.filter(order__created_at__gte=sixty_days_ago, order__created_at__lt=thirty_days_ago)\
            .values('variant__product')\
            .annotate(units_sold=Count('id'))
        prev_period_map = {row['variant__product']: row['units_sold'] for row in prev_period_orders}

        for t in trending:
            product_id = t['variant__product']
            product_obj = products_map.get(product_id)
            if not product_obj:
                continue
            this_units = period_map.get(product_id, 0)
            prev_units = prev_period_map.get(product_id, 0)
            # Calculate trend_percent
            if prev_units == 0 and this_units == 0:
                trend_percent = None
            elif prev_units == 0:
                trend_percent = 100 
            else:
                trend_percent = round(((this_units - prev_units) / prev_units) * 100)
            trending_products_list.append({
                'id': product_id,
                'name': product_obj.name,
                'units_sold': t['units_sold'],
                'revenue': float(t['revenue']) if t['revenue'] else 0,
                'trend_percent': trend_percent
            })

        # Wishlisted Most calculations
        most_wishlisted_variants = (
            ProductVariant.objects
            .annotate(wishlist_count=Count('wishlist', distinct=True))
            .order_by('-wishlist_count', 'id')[:5]
        )
        most_wishlisted_products = [variant.product for variant in most_wishlisted_variants]
        most_wishlisted_with_count = [
            {'variant': variant, 'wishlist_count': variant.wishlist_count}
            for variant in most_wishlisted_variants
        ]

        # Chart Data Calculations
        from django.db.models.functions import TruncMonth, TruncWeek
        import json
        
        # 1. Sales Value (Last 12 Months) - DUMMY DATA
        # last_year = today - timedelta(days=365)
        # monthly_sales = (
        #     Order.objects.filter(created_at__gte=last_year)
        #     .annotate(month=TruncMonth('created_at'))
        #     .values('month')
        #     .annotate(total_revenue=models.Sum('total_amount'))
        #     .order_by('month')
        # )
        # Prepare data for Chart.js (labels and data)
        # sales_month_labels = [entry['month'].strftime('%b') for entry in monthly_sales]
        # sales_month_data = [float(entry['total_revenue'] or 0) for entry in monthly_sales]
        
        sales_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        sales_month_data = [25000, 20000, 30000, 22000, 17000, 29000, 45000, 50000, 40000, 60000, 70000, 80000]

        # 2. Sales Value (Last 4 Weeks) - DUMMY DATA
        # weekly_sales = (
        #     Order.objects.filter(created_at__gte=thirty_days_ago)
        #     .annotate(week=TruncWeek('created_at'))
        #     .values('week')
        #     .annotate(total_revenue=models.Sum('total_amount'))
        #     .order_by('week')
        # )
        # sales_week_labels = [entry['week'].strftime('%d %b') for entry in weekly_sales]
        # sales_week_data = [float(entry['total_revenue'] or 0) for entry in weekly_sales]
        
        sales_week_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        sales_week_data = [5000, 7000, 6000, 8000]

        # 3. Performance (Total Orders per Month - Last 12 Months) - DUMMY DATA
        # monthly_orders = (
        #     Order.objects.filter(created_at__gte=last_year)
        #     .annotate(month=TruncMonth('created_at'))
        #     .values('month')
        #     .annotate(total_orders=Count('id'))
        #     .order_by('month')
        # )
        # orders_month_labels = [entry['month'].strftime('%b') for entry in monthly_orders]
        # orders_month_data = [entry['total_orders'] for entry in monthly_orders]
        
        orders_month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        orders_month_data = [10, 20, 15, 30, 25, 40, 35, 50, 45, 60, 55, 70]

        context = {
            'most_wishlisted_variants': most_wishlisted_variants,
            'most_wishlisted_products': most_wishlisted_products,
            'most_wishlisted_with_count': most_wishlisted_with_count,
            'trending_products': trending_products_list,
            # Chart Data (JSON serialized)
            'sales_month_labels': json.dumps(sales_month_labels),
            'sales_month_data': json.dumps(sales_month_data),
            'sales_week_labels': json.dumps(sales_week_labels),
            'sales_week_data': json.dumps(sales_week_data),
            'orders_month_labels': json.dumps(orders_month_labels),
            'orders_month_data': json.dumps(orders_month_data),
        }

        return render(request, self.template_name, context)


class ViewNotifications(View):
    def get(self, request):
        dashboard_notifications = (
            Notification.objects
            .select_related("user")
            .order_by('-created_at')
        )
        return render(request, 'profile/notifications.html', {
            'dashboard_notifications': dashboard_notifications,
        })


class ProfileView(View):
    template_name = 'profile/profile.html'

    def get(self, request):
        user_profile = request.user
        try:
            company_contact = CompanyContact.objects.get(user=user_profile)
        except CompanyContact.DoesNotExist:
            company_contact = None

        context = {
            'user': user_profile,
            'user_profile': user_profile,
            'contact': company_contact,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        user_profile = request.user

        if 'first_name' in request.POST and 'last_name' in request.POST:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            address = request.POST.get('address', '').strip()
            avatar = request.FILES.get('avatar')

            user_profile.first_name = first_name
            user_profile.last_name = last_name
            if address:
                user_profile.address = address
            if avatar:
                user_profile.avatar = avatar
            user_profile.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')

        elif 'company_name' in request.POST: 
            company_name = request.POST.get('company_name', '').strip()
            company_email = request.POST.get('company_email', '').strip()
            company_phone = request.POST.get('company_phone', '').strip()
            company_website = request.POST.get('company_website', '').strip()
            company_address = request.POST.get('company_address', '').strip()
            company_city = request.POST.get('company_city', '').strip()
            company_state = request.POST.get('company_state', '').strip()
            company_zip = request.POST.get('company_zip', '').strip()

            contact, created = CompanyContact.objects.get_or_create(user=user_profile)
            contact.company_name = company_name
            contact.company_email = company_email
            contact.company_phone = company_phone
            contact.company_website = company_website
            contact.company_address = company_address
            contact.company_city = company_city
            contact.company_state = company_state
            contact.company_zip = company_zip
            contact.save()
            messages.success(request, "Company contact details have been updated.")
            return redirect('profile')

        return redirect('profile')



@method_decorator(csrf_exempt, name='dispatch')
class DeleteNotificationView(View):
    def post(self, request, notif_id):
        if not request.user.is_authenticated:
            messages.error(request, "You need to be logged in to perform this action.")
            return redirect('notification_list')
        try:
            notification = Notification.objects.get(id=notif_id, user=request.user)
            notification.delete()
        except Notification.DoesNotExist:
            messages.error(request, "Notification not found.")
        return redirect('notification_list')


@method_decorator(csrf_exempt, name='dispatch')
class ClearAllNotificationsView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You need to be logged in to perform this action.")
            return redirect('notification_list')
        Notification.objects.filter(user=request.user).delete()
        return redirect('notification_list')


class MarkNotificationAsReadView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, notif_id):
        if not notif_id:
            return Response({"success": False, "error": "Notification id required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            notification = Notification.objects.get(id=notif_id)
        except Notification.DoesNotExist:
            return Response({'success': False, 'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not notification.is_read:
            notification.mark_as_read()
        return Response({'success': True}, status=status.HTTP_200_OK)




@method_decorator(csrf_protect, name='dispatch')
class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('email')
        password = request.POST.get('password')
        print(username,'dd',password)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, self.template_name)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


                                        ## CATEGORY VIEWS ##

class ProductCategoryView(PaginationSearchMixin, View):
    template_name = 'products/category.html'
    search_fields = ['category_name']
    fields = []


    def get(self, request):
        categories = Categories.objects.filter()
        search_query = request.GET.get('q', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_categories = self.filter_queryset(categories, search_query, filter_fields)
        categories_page = self.paginate_queryset(request, filtered_categories)
        return render(request, self.template_name, {
            'categories': categories_page,
            'search_query': search_query,
            'filter_fields': filter_fields,
        })




# Django form for category
class CategoryCreateView(View):
    def post(self, request):
        form = CategoriesForm(request.POST, request.FILES)
        if form.is_valid():
            category_name = form.cleaned_data.get('category_name')
            if Categories.objects.filter(category_name__iexact=category_name).exists():
                messages.error(request, "Category with this name already exists.", extra_tags="category-error")
                return redirect('product_category')
            form.save()
            messages.success(request, "Category created successfully.", extra_tags="category-success")
            return redirect('product_category')

        messages.error(request, "Category creation failed.", extra_tags="category-error")
        return redirect('product_category')


class CategoryEditView(View):
    def post(self, request, pk):
        category = get_object_or_404(Categories, pk=pk)
        form = CategoriesForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category_name = form.cleaned_data.get('category_name')
            if Categories.objects.filter(category_name__iexact=category_name).exclude(pk=pk).exists():
                messages.error(request, "Another category with this name already exists.", extra_tags="category-error")
                return redirect('product_category')
            form.save()
            messages.success(request, "Category updated successfully.", extra_tags="category-success")
            return redirect('product_category')

        messages.error(request, "Category update failed.", extra_tags="category-error")
        return redirect('product_category')


class CategoryDeleteView(View):
    def get(self, request, pk):
        try:
            category = get_object_or_404(Categories, pk=pk)
            category.delete()
            messages.success(request, "Category deleted successfully.", extra_tags="category-sucess")
        except Exception as e:
            messages.error(request, f"Failed to delete category: {str(e)}", extra_tags="category-error")
        return redirect('product_category')



                                                    ## COLORS ##
# Color views have been commented out as color functionality is being removed
# Uncomment if you need to re-enable color management

# class ProductColorsView(PaginationSearchMixin, View):
#     template_name = 'products/colors.html'
#     search_fields = ['name', 'value']
#     fields = []

#     def get(self, request):
#         colors = Colors.objects.all()
#         search_query = request.GET.get('search', '').strip()
#         filter_fields = self.get_filter_fields(request)
#         filtered_colors = self.filter_queryset(colors, search_query, filter_fields)
#         colors_page = self.paginate_queryset(request, filtered_colors)
#         return render(request, self.template_name, {
#             'colors': colors_page,
#             'search_query': search_query,
#             'filter_fields': filter_fields,
#         })


# class ProductColorCreateView(View):
#     def post(self, request):
#         form = ProductColorForm(request.POST)
#         if form.is_valid():
#             name = form.cleaned_data.get('name')
#             value = form.cleaned_data.get('value')
#             if Colors.objects.filter(name__iexact=name, color__iexact=value).exists():
#                 messages.error(request, "Color with this name and value already exists.", extra_tags="color-error")
#                 return redirect('product_colors')
#             form.save()
#             messages.success(request, "Color created successfully.", extra_tags="color-success")
#             return redirect('product_colors')
#         messages.error(request, "Color creation failed.", extra_tags="color-error")
#         return redirect('product_colors')


# class ProductColorEditView(View):
#     def post(self, request, pk):

#         color = get_object_or_404(Colors, pk=pk)
#         form = ProductColorForm(request.POST, instance=color)
#         if form.is_valid():
#             name = form.cleaned_data.get('name')
#             value = form.cleaned_data.get('value')
#             if Colors.objects.filter(name__iexact=name, color__iexact=value).exclude(pk=pk).exists():
#                 messages.error(request, "Another color with this name and value already exists.", extra_tags="color-error")
#                 return redirect('product_colors')
#             form.save()
#             messages.success(request, "Color updated successfully.", extra_tags="color-success")
#             return redirect('product_colors')
#         messages.error(request, "Color update failed.", extra_tags="color-error")
#         return redirect('product_colors')


# class ProductColorDeleteView(View):
#     def get(self, request, color_id):
#         try:
#             color = get_object_or_404(Colors, pk=color_id)
#             color.delete()
#             messages.success(request, "Color deleted successfully.", extra_tags="color-success")
#         except Exception as e:
#             messages.error(request, f"Failed to delete color: {str(e)}", extra_tags="color-error")
#         return redirect('product_colors')



        
                                            ## PRODUCTS ##

class ProductsView(PaginationSearchMixin, View):
    template_name = 'products/products.html'
    search_fields = ['name', 'title', 'description', 'base_price','category']
    fields = []

    def get(self, request):
        products = Product.objects.select_related('category').all()
        search_query = request.GET.get('search', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_products = self.filter_queryset(products, search_query, filter_fields)
        products_page = self.paginate_queryset(request, filtered_products)
        return render(request, self.template_name, {
            'products': products_page,
            'search_query': search_query,
            'filter_fields': filter_fields,
            'categories': Categories.objects.all(),
        })


class ProductCreateView(View):
    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            if Product.objects.filter(name__iexact=name).exists():
                messages.error(request, "Product with this name already exists.", extra_tags="product-error")
                return redirect('products')
            form.save()
            messages.success(request, "Product created successfully.", extra_tags="product-success")
            return redirect('products')
        print(form.errors)
        messages.error(request, "Product creation failed.", extra_tags="product-error")
        return redirect('products')


class ProductEditView(View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            name = form.cleaned_data.get('name')
            if Product.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                messages.error(request, "Another product with this name already exists.", extra_tags="product-error")
                return redirect('products')
            form.save()
            messages.success(request, "Product updated successfully.", extra_tags="product-success")
            return redirect('products')
        messages.error(request, "Product update failed.", extra_tags="product-error")
        return redirect('products')

class ProductDeleteView(View):
    def get(self, request, product_id):
        try:
            product = get_object_or_404(Product, pk=product_id)
            product.delete()
            messages.success(request, "Product deleted successfully.", extra_tags="product-success")
        except Exception as e:
            messages.error(request, f"Failed to delete product: {str(e)}", extra_tags="product-error")
        return redirect('products')


                                            ## PRODUCT VARIANTS ##



class ProductVariantsView(PaginationSearchMixin, View):
    template_name = 'products/variants.html'
    search_fields = ['product', 'size', 'price', 'variant']
    fields = []

    def get(self, request):
        variants = ProductVariant.objects.select_related('product').all()
        search_query = request.GET.get('search', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_variants = self.filter_queryset(variants, search_query, filter_fields)
        variants_page = self.paginate_queryset(request, filtered_variants)
        return render(request, self.template_name, {
            'variants': variants_page,
            'search_query': search_query,
            'filter_fields': filter_fields,
            'products':Product.objects.all(),
            'sizes':Sizes.objects.all(),
        })


class ProductVariantCreateView(View):
    def post(self, request):
        form = ProductVariantForm(request.POST)
        images = request.FILES.getlist('variant_images')
       
        if form.is_valid():
            product = form.cleaned_data.get('product')
            size = form.cleaned_data.get('size')
            variant_name = form.cleaned_data.get('variant')

            # Check for existing variant with same product and size (color is optional now)
            if ProductVariant.objects.filter(product=product, size=size,variant=variant_name).exists():
                messages.error(request, "Variant with these attributes already exists.", extra_tags="variant-error")
                return redirect('product_variants')

            variant = form.save()
            if images:
                for idx, image in enumerate(images, start=1):
                    ProductImage.objects.create(variant=variant, image=image, order_by=idx)

            messages.success(request, "Variant created successfully.", extra_tags="variant-success")
            return redirect('product_variants')
        messages.error(request, "Variant creation failed.", extra_tags="variant-error")
        return redirect('product_variants')


class ProductVariantEditView(View):
    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)
        form = ProductVariantForm(request.POST, instance=variant)
        images = request.FILES.getlist('variant_images')
        print(images,'asdf')
        if form.is_valid():
            product = form.cleaned_data.get('product')
            size = form.cleaned_data.get('size')
            variant_name = form.cleaned_data.get('variant')

            # Check for existing variant with same product and size (excluding current variant)
            if ProductVariant.objects.filter(
                product=product,
                size=size,
                variant=variant_name
            ).exclude(pk=pk).exists():
                messages.error(request, "Another variant with these attributes already exists.", extra_tags="variant-error")
                return redirect('product_variants')

            form.save()

            if images:
                last_order = ProductImage.objects.filter(variant=variant).aggregate(max_order=models.Max('order_by'))['max_order'] or 0
                for idx, image in enumerate(images, start=1):
                    ProductImage.objects.create(variant=variant, image=image, order_by=last_order + idx)

            messages.success(request, "Variant updated successfully.", extra_tags="variant-success")
            return redirect('product_variants')
        messages.error(request, "Variant update failed.", extra_tags="variant-error")
        return redirect('product_variants')


class ProductVariantDeleteView(View):
    def get(self, request, variant_id):
        try:
            variant = get_object_or_404(ProductVariant, pk=variant_id)
            variant.delete()
            messages.success(request, "Variant deleted successfully.", extra_tags="variant-success")
        except Exception as e:
            messages.error(request, f"Failed to delete variant: {str(e)}", extra_tags="variant-error")
        return redirect('product_variants')


@method_decorator(csrf_exempt, name='dispatch')
class CareGuideListView(View):
    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        guides = variant.care_guides.all().order_by('order', '-created_at')
        data = []
        for guide in guides:
            data.append({
                'id': guide.id,
                'title': guide.title,
                'content': guide.content,
                'is_active': guide.is_active,
                'order': guide.order,
            })
        return JsonResponse({'success': True, 'guides': data})


@method_decorator(csrf_exempt, name='dispatch')
class CareGuideCreateView(View):
    def post(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        form = CareGuideForm(request.POST)
        if form.is_valid():
            guide = form.save(commit=False)
            guide.variant = variant
            guide.save()
            return JsonResponse({
                'success': True, 
                'message': 'Care guide added successfully.',
                'guide': {
                    'id': guide.id,
                    'title': guide.title,
                    'content': guide.content,
                    'is_active': guide.is_active,
                    'order': guide.order,
                }
            })
        return JsonResponse({'success': False, 'message': 'Invalid data.', 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class CareGuideEditView(View):
    def post(self, request, pk):
        guide = get_object_or_404(CareGuide, pk=pk)
        form = CareGuideForm(request.POST, instance=guide)
        if form.is_valid():
            guide = form.save()
            return JsonResponse({
                'success': True, 
                'message': 'Care guide updated successfully.',
                'guide': {
                    'id': guide.id,
                    'title': guide.title,
                    'content': guide.content,
                    'is_active': guide.is_active,
                    'order': guide.order,
                }
            })
        return JsonResponse({'success': False, 'message': 'Invalid data.', 'errors': form.errors}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class CareGuideDeleteView(View):
    def post(self, request, pk):
        try:
            guide = get_object_or_404(CareGuide, pk=pk)
            guide.delete()
            return JsonResponse({'success': True, 'message': 'Care guide deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Failed to delete care guide: {str(e)}'}, status=400)



@method_decorator(csrf_exempt, name='dispatch')
class CareGuideTemplatesView(View):
    def get(self, request):
        # Get unique guides based on title and content to avoid duplicates in the dropdown
        templates = CareGuide.objects.values('title', 'content').distinct().order_by('title')
        return JsonResponse({'success': True, 'templates': list(templates)})


@method_decorator(csrf_exempt, name='dispatch')
class DeleteVariantImageView(View):
    def post(self, request, image_id):
        try:
            image = get_object_or_404(ProductImage, pk=image_id)
            image.delete()
            # messages.success(request, "Image deleted successfully.", extra_tags="variant-success")
            return JsonResponse({'success': True, 'message': 'Image deleted successfully.'})
        except Exception as e:
            # messages.error(request, f"Failed to delete image: {str(e)}", extra_tags="variant-error")
            return JsonResponse({'success': False, 'message': f'Failed to delete image: {str(e)}'}, status=400)



class OrdersDashboardView(PaginationSearchMixin, View):
    template_name = 'orders/orders.html'
    search_fields = ['id', 'user__email', 'items__product__name']
    paginate_by = 10

    def get_filter_fields(self, request):
        return {
            'start_date': request.GET.get('start_date', ''),
            'end_date': request.GET.get('end_date', ''),
            'status': request.GET.get('status', ''),
            'product': request.GET.get('product', ''),
            'customer': request.GET.get('customer', ''),
            'min_amount': request.GET.get('min_amount', ''),
            'max_amount': request.GET.get('max_amount', ''),
        }

    def get(self, request):
        orders = Order.objects.select_related('user', 'shipping_address', 'coupon').prefetch_related('items__variant__product').all()

        # Apply search filter
        search_query = request.GET.get('search', '').strip()
        if search_query:
            query = Q()
            for field in self.search_fields:
                if field == 'id':
                    try:
                        query |= Q(id=int(search_query))
                    except ValueError:
                        pass
                elif field == 'user__email':
                    query |= Q(user__email__icontains=search_query)
                elif field == 'items__product__name':
                    query |= Q(items__variant__product__name__icontains=search_query)
            orders = orders.filter(query).distinct()

        # Apply additional filters
        filters = self.get_filter_fields(request)

        if filters['start_date']:
            try:
                orders = orders.filter(created_at__date__gte=filters['start_date'])
            except ValueError:
                pass

        if filters['end_date']:
            try:
                orders = orders.filter(created_at__date__lte=filters['end_date'])
            except ValueError:
                pass

        if filters['status']:
            orders = orders.filter(status=filters['status'])

        if filters['product']:
            try:
                orders = orders.filter(items__variant__product__id=filters['product'])
            except ValueError:
                pass

        if filters['customer']:
            try:
                orders = orders.filter(user__id=filters['customer'])
            except ValueError:
                pass

        if filters['min_amount']:
            try:
                orders = orders.filter(total_amount__gte=float(filters['min_amount']))
            except ValueError:
                pass

        if filters['max_amount']:
            try:
                orders = orders.filter(total_amount__lte=float(filters['max_amount']))
            except ValueError:
                pass


        paginated_orders = self.paginate_queryset(request, orders)

        # Prepare context for the template
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)

        context = {
            'orders': paginated_orders,
            'order_statuses': [choice[0] for choice in Order.STATUS_CHOICES],
            'products': Product.objects.all(),
            'customers': Profile.objects.all(),
            'today': today,
            'week_ago': week_ago,
            'month_ago': month_ago,
            'year_ago': year_ago,
        }

        return render(request, self.template_name, context)

class OrderDetailView(View):
    template_name = 'orders/order_details.html'

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        order_items = order.items.select_related('variant__product', 'variant__size').all()
        order_statuses = [choice[0] for choice in Order.STATUS_CHOICES]


        context = {
            'order': order,
            'order_items': order_items,
            'order_statuses': order_statuses,
        }
        return render(request, self.template_name, context)

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status and new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f"Order status updated to '{new_status.title()}'.")
        else:
            messages.error(request, "Invalid status.")
        return redirect('order_detail', order_id=order.id)



class DownloadOrdersExcelView(PaginationSearchMixin, View):
    def get_filter_fields(self, request):
        return super().get_filter_fields(request)

    def get_search_query(self, request):
        return super().get_search_query(request)

    search_fields = ['id', 'user__email', 'items__product__name']
    fields = ['start_date', 'end_date', 'status', 'product', 'customer', 'min_amount', 'max_amount']

    def get(self, request):
        orders = Order.objects.select_related('user', 'shipping_address', 'coupon').prefetch_related('items__variant__product').all()

        search_query = self.get_search_query(request)
        filter_fields = self.get_filter_fields(request)

        if search_query:
            query = Q()
            for field in self.search_fields:
                if field == 'id':
                    try:
                        query |= Q(id=int(search_query))
                    except ValueError:
                        pass
                elif field == 'user__email':
                    query |= Q(user__email__icontains=search_query)
                elif field == 'items__product__name':
                    query |= Q(items__variant__product__name__icontains=search_query)
            orders = orders.filter(query).distinct()

        if filter_fields.get('start_date'):
            try:
                orders = orders.filter(created_at__date__gte=filter_fields['start_date'])
            except ValueError:
                pass

        if filter_fields.get('end_date'):
            try:
                orders = orders.filter(created_at__date__lte=filter_fields['end_date'])
            except ValueError:
                pass

        if filter_fields.get('status'):
            orders = orders.filter(status=filter_fields['status'])

        if filter_fields.get('product'):
            try:
                orders = orders.filter(items__variant__product__id=filter_fields['product'])
            except ValueError:
                pass

        if filter_fields.get('customer'):
            try:
                orders = orders.filter(user__id=filter_fields['customer'])
            except ValueError:
                pass

        if filter_fields.get('min_amount'):
            try:
                orders = orders.filter(total_amount__gte=float(filter_fields['min_amount']))
            except ValueError:
                pass

        if filter_fields.get('max_amount'):
            try:
                orders = orders.filter(total_amount__lte=float(filter_fields['max_amount']))
            except ValueError:
                pass

        # Manually define columns for export
        columns = [
            ("order_id", "Order ID"),
            ("customer_name", "Customer Name"),
            ("customer_email", "Customer Email"),
            ("products", "Products"),
            ("status", "Status"),
            ("total_amount", "Total Amount"),
            ("created_at", "Created"),
        ]

        data = []
        for order in orders.select_related("user").prefetch_related("items__variant__product"):
            row = {}

            row["order_id"] = order.id
            row["customer_name"] = f"{order.user.first_name} {order.user.last_name}" if order.user else ""
            row["customer_email"] = order.user.email if order.user else ""

            product_names = []
            for item in order.items.all():
                product_name = ""
                if hasattr(item, "variant") and hasattr(item.variant, "product"):
                    product_name = getattr(item.variant.product, "name", "")
                if product_name:
                    product_names.append(product_name)

            row["products"] = ", ".join(product_names)
            row["status"] = order.status
            row["total_amount"] = f"{order.total_amount:.2f}" if order.total_amount is not None else ""
            row["created_at"] = date_format(order.created_at, "Y-m-d H:i:s") if order.created_at else ""

            data.append(row)
        return download_excel_dynamic(data, columns, filename_prefix="orders_export")



class DownloadOrderPDFView(View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)


        order.invoice_number = self.generate_invoice_number(order)
        order.save()

        items = order.items.select_related("variant__product")
        table_rows = []
        subtotal = 0

        for item in items:
            product_name = ""
            if hasattr(item, "variant") and hasattr(item.variant, "product"):
                product_name = getattr(item.variant.product, "name", "")

            variant_details = []
            if hasattr(item.variant, "color") and item.variant.color:
                variant_details.append(str(item.variant.color))
            if hasattr(item.variant, "size") and item.variant.size:
                variant_details.append(str(item.variant.size))

            line_total = (item.price * item.quantity) if (item.price is not None and item.quantity) else 0
            subtotal += line_total

            table_rows.append([
                product_name,
                " | ".join(variant_details) if variant_details else "",
                item.quantity,
                f"${item.price:.2f}" if item.price is not None else "$0.00",
                f"${line_total:.2f}",
            ])

        # Prepare columns & headers for PDF
        columns = [
            ("product", "Product"),
            ("variant", "Variant"),
            ("quantity", "Qty"),
            ("unit_price", "Unit Price"),
            ("total", "Line Total"),
        ]
        headers = [header for field, header in columns]

        # Prepare context for pdf/invoice.html
        context = {
            "order": order,
            "rows": table_rows,
            "headers": headers,
            "subtotal": subtotal,
            "title": "Invoice"
        }

        # Render the invoice HTML template as a string
        from django.template.loader import render_to_string
        html_string = render_to_string('pdf/invoice.html', context)

        # generate_pdf_dynamic: data and columns needed for base template; also pass HTML
        return generate_pdf_dynamic(
            data=[],  # not needed when html supplied
            columns=columns,
            filename_prefix=f"invoice_{order.invoice_number}",
            html=html_string
        )

    @staticmethod
    def generate_invoice_number(order=None):
        """
        Generate unique invoice number with format: INV-YYYY-XXXXX.
        Ensures the invoice number is unique for the Order.
        """
        from django.db import transaction

        with transaction.atomic():
            current_year = datetime.now().year
            prefix = f'INV-{current_year}'

            # Ensure uniqueness by using the order's pk if available
            if order and order.pk:
                number = order.pk
            else:
                last_order = Order.objects.select_for_update().order_by('-id').first()
                if last_order:
                    number = last_order.id + 1
                else:
                    number = 1

            return f'{prefix}-{number:05d}'


                                                    ## CUSTOMERS ##

class CustomersView(PaginationSearchMixin, View):
    template_name = 'customers/customers.html'
    fields = ['phone', 'date_joined']
    search_fields = ['first_name', 'last_name', 'email', 'phone']

    def get_queryset(self):
        return Profile.objects.filter(is_active=True).order_by('-id')

    def get(self, request):
        queryset = self.get_queryset()
        search_query = request.GET.get('search', '').strip()

        filter_fields = {}
        for field in self.fields:
            value = request.GET.get(field)
            if value:
                filter_fields[field] = value
        if filter_fields:
            queryset = queryset.filter(**filter_fields)

        customers_page = self.paginate_queryset(request, queryset)

        return render(request, self.template_name, {
            'customers': customers_page,
            'search_query': search_query,
            'filter_fields': filter_fields,
        })


                                               

### Sizes ###

class SizesView(PaginationSearchMixin, View):
    template_name = 'products/size.html'
    search_fields = ['size_name']
    fields = []

    def get(self, request):
        sizes = Sizes.objects.filter()
        search_query = request.GET.get('q', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_sizes = self.filter_queryset(sizes, search_query, filter_fields)
        sizes_page = self.paginate_queryset(request, filtered_sizes)
        return render(request, self.template_name, {
            'sizes': sizes_page,
            'search_query': search_query,
            'filter_fields': filter_fields,
        })


class SizeCreateView(View):
    def post(self, request):
        form = SizeForm(request.POST)
        if form.is_valid():
            size_name = form.cleaned_data.get('size_name')
            if Sizes.objects.filter(size__iexact=size_name).exists():
                messages.error(request, "Size with this name already exists.", extra_tags="size-error")
                return redirect('product_size')
            form.save()
            messages.success(request, "Size created successfully.", extra_tags="size-success")
            return redirect('product_size')

        print(form.errors)
        messages.error(request, "Size creation failed.", extra_tags="size-error")
        return redirect('product_size')


class SizeEditView(View):
    def post(self, request, pk):
        size = get_object_or_404(Sizes, pk=pk)
        form = SizeForm(request.POST, instance=size)
        if form.is_valid():
            size_name = form.cleaned_data.get('size')
            if Sizes.objects.filter(size__iexact=size_name).exclude(pk=pk).exists():
                messages.error(request, "Another size with this name already exists.", extra_tags="size-error")
                return redirect('product_size')
            form.save()
            messages.success(request, "Size updated successfully.", extra_tags="size-success")
            return redirect('product_size')
        print(form.errors)
        messages.error(request, "Size update failed.", extra_tags="size-error")
        return redirect('product_size')


class SizeDeleteView(View):
    def get(self, request, pk):
        try:
            size = get_object_or_404(Sizes, pk=pk)
            size.delete()
            messages.success(request, "Size deleted successfully.", extra_tags="size-success")
        except Exception as e:
            messages.error(request, f"Failed to delete size: {str(e)}", extra_tags="size-error")
        return redirect('product_size')


## Product Store 
class ProductStore(View):
    def get(self, request):
        products_list = ProductVariant.objects.filter().order_by('-created_at')
        return render(request, 'products/product_store.html', {'products_list': products_list})


class PaymentView(View):
    def get(self,request):
        return render(request,'orders/payment.html')


class IconsView(View):
    template_name = 'home/icons.html'

    def get(self, request):
        return render(request, self.template_name)
        


                                                    # Coupon code


class CouponListView(PaginationSearchMixin, View):
    template_name = 'offers/coupon.html'
    search_fields = ['name', 'code']
    paginate_by = 10
    fields=['name', 'code']

    def get(self, request):
        queryset = Coupon.objects.filter(active_status=True).order_by('-created_at')
        search_query = request.GET.get('search', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_items = self.filter_queryset(queryset, search_query, filter_fields)
        coupons_page = self.paginate_queryset(request, filtered_items)
        context = {
            'coupons': coupons_page,
            'search_query': request.GET.get('search', '').strip() or request.GET.get('q', '').strip(),
        }
        return render(request, self.template_name, context)


class CouponCreateView(View):
    def post(self, request):
        form = CouponForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            if Coupon.objects.filter(code__iexact=code).exists():
                messages.error(request, "Coupon code already exists.")
                return redirect('coupon')

            form.save()
            messages.success(request, "Coupon created successfully.",extra_tags="coupon-success")
            return redirect('coupon')
        else:
            print(form.errors,'sadfafd')
            messages.error(request, "Please fill all required fields.",extra_tags="coupon-error")
            return redirect('coupon')



class CouponEditView(View):
    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        active_status = request.POST.get('active')
        if active_status is not None:
            coupon.active = active_status.lower() in ['true', '1', 'on', 'yes']
            coupon.save()
            messages.success(request, "Coupon active status updated.", extra_tags="coupon-success")
        else:
            messages.error(request, "Please provide the active status.", extra_tags="coupon-error")
        return redirect('coupon')



class CouponDeleteView(View):
    def get(self, request, pk):
        try:
            coupon = Coupon.objects.get(pk=pk)
            coupon.active_status = False
            coupon.deleted_at = timezone.now()
            coupon.save()
            messages.success(request, "Coupon deleted successfully.", extra_tags="coupon-success")
        except Coupon.DoesNotExist:
            messages.error(request, "Coupon not found.", extra_tags="coupon-error")
        return redirect('coupon')


## Terms and conditions 
class TermsConditionListView(View):
    template_name = 'tandc/tandc.html'
    paginate_by = 10

    def get(self, request):
        terms_conditions = TermsCondition.objects.all().order_by('-created_at')

        return render(request, self.template_name, {
            'terms': terms_conditions,
        })


class TermsConditionCreateView(View):
    template_name = 'tandc/add_tandc.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            if TermsCondition.objects.filter(title__iexact=title).exists():
                messages.error(request, "A term with this title already exists.", extra_tags='tandc-error')
                return redirect('terms_condition_list')
            TermsCondition.objects.create(title=title, content=content)
            messages.success(request, "Terms & Condition added successfully.", extra_tags='tandc-success')
            return redirect('terms_condition_list')
        messages.error(request, "Both Title and Content are required.", extra_tags='tandc-error')
        return redirect('terms_condition_list')


class TermsConditionEditView(View):
    template_name = 'tandc/edit_tandc.html'

    def get(self, request, pk):
        term = get_object_or_404(TermsCondition, pk=pk)
        return render(request, self.template_name, {'term': term})

    def post(self, request, pk):
        term = get_object_or_404(TermsCondition, pk=pk)
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            if TermsCondition.objects.filter(title__iexact=title).exclude(pk=pk).exists():
                messages.error(request, "Another term with this title already exists.", extra_tags='tandc-error')
                return redirect('terms_condition_list')
            term.title = title
            term.content = content
            term.save()
            messages.success(request, "Terms & Condition updated successfully.", extra_tags='tandc-success')
            return redirect('terms_condition_list')
        messages.error(request, "Both Title and Content are required.", extra_tags='tandc-error')
        return redirect('terms_condition_list')


class TermsConditionDeleteView(View):
    def post(self, request, pk):
        try:
            term = get_object_or_404(TermsCondition, pk=pk)
            term.delete()
            messages.success(request, "Terms & Condition deleted successfully.", extra_tags='tandc-success')
        except Exception as e:
            messages.error(request, f"Failed to delete Terms & Condition: {str(e)}", extra_tags='tandc-error')
        return redirect('terms_condition_list')


## Contact us
class ContactUsListView(PaginationSearchMixin, View):
    template_name = 'contact/contact.html'
    search_fields = ['name', 'email', 'phone', 'content']
    paginate_by = 10

    def get(self, request):
        queryset = ContactUs.objects.all().order_by('-created_at')
        search_query = request.GET.get('search', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_contacts = self.filter_queryset(queryset, search_query, filter_fields)
        contacts_page = self.paginate_queryset(request, filtered_contacts)
        context = {
            'contacts': contacts_page,
            'search_query': search_query,
        }
        return render(request, self.template_name, context)


class ContactUsDeleteView(View):
    def get(self, request, pk):
        try:
            contact = get_object_or_404(ContactUs, pk=pk)
            contact.delete()
            messages.success(request, "Contact submission deleted successfully.", extra_tags='contact-success')
        except Exception as e:
            messages.error(request, f"Failed to delete contact submission: {str(e)}", extra_tags='contact-error')
        return redirect('contact_us')



class ReplyContactUsView(View):
    def post(self, request, pk):
        try:
            contact = get_object_or_404(ContactUs, pk=pk) 
            reply_content = request.POST.get('reply', '').strip()

            if not reply_content:
                messages.error(request, "Reply content cannot be empty.")
                return redirect('contact_us')

            # Save reply
            contact.reply = reply_content
            contact.is_replied = True
            contact.replied_at = timezone.now()
            contact.save()

            # Prepare context for email template
            context = {
                'user_name': contact.name.strip() or 'Valued Customer',
                'reply_content': reply_content,
                'company_name': getattr(settings, 'COMPANY_NAME', 'Our Company'),
                'current_year': timezone.now().year,
            }

            # Render HTML email
            html_content = render_to_string('emails/contact.html', context)
            text_content = strip_tags(html_content)  # Plain text fallback

            # Create email
            subject = f"Re: {contact.subject}" if contact.subject else "Reply from Our Team"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [contact.email]

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipient_list,
                reply_to=[from_email],  # Good practice: allow direct reply
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            messages.success(
                request,
                f"Reply sent successfully to {contact.email}",
                extra_tags='contact-success'
            )
        except Exception as e:
            print(e)
            messages.error(
                request,
                f"Failed to send reply: {str(e)}",
                extra_tags='contact-error'
            )

        return redirect('contact_us')


## Payment
class PaymentGatewayListView(PaginationSearchMixin, View):
    template_name = 'gateway/gateway.html'
    paginate_by = 10
    search_fields = ['name', 'display_name']  

    def get(self, request):
        queryset = PaymentGateway.objects.all().order_by('priority', 'display_name')
        search_query = request.GET.get('search', '').strip()
        filter_fields = self.get_filter_fields(request)
        filtered_gateways = self.filter_queryset(queryset, search_query, filter_fields)
        gateways_page = self.paginate_queryset(request, filtered_gateways)
        form = PaymentGatewayForm()

        context = {
            'gateways': gateways_page,
            'search_query': search_query or request.GET.get('q', '').strip(),
            'form': form,

        }
        return render(request, self.template_name, context)



class PaymentGatewayCreateView(View):
    def post(self, request):
        form = PaymentGatewayForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                instance = form.save(commit=False)
                instance.created_by = request.user
                instance.save()
                messages.success(request, "Payment Gateway created successfully.", extra_tags='gateway-success')
                return redirect('payment_gateway_list')
            except Exception as e:
                messages.error(request, f"Failed to create Payment Gateway: {e}", extra_tags='gateway-error')
        else:
            messages.error(request, "Please correct the errors below.", extra_tags='gateway-error')
        return redirect('payment_gateway_list')