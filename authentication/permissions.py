from django.http import HttpResponseForbidden
from django.shortcuts import redirect

class UserPermissionMixin:
    """
    Mixin to allow access only to users with user_type 'user'.
    Use this mixin with class-based views.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and getattr(user, 'user_type', None) == 'user'):
            return redirect('loging')
        return super().dispatch(request, *args, **kwargs)


class AdminPermissionMixin:
    """
    Mixin to allow access only to users with user_type 'admin' and superuser status.
    Use this mixin with class-based views.
    """
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_authenticated and user.is_superuser and getattr(user, 'user_type', None) == 'admin'):
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


from rest_framework.permissions import BasePermission


class IsUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'user_type', None) == 'user')


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser and getattr(user, 'user_type', None) == 'admin')
