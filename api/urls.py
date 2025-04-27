from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AddressViewSet, DriverViewSet, RequestServiceView, CompleteServiceView

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'drivers', DriverViewSet, basename='driver')

urlpatterns = [
    path('', include(router.urls)),
    path('services/request/', RequestServiceView.as_view(), name='request-service'),
    path('services/<int:pk>/complete/', CompleteServiceView.as_view(), name='complete-service'),
] 