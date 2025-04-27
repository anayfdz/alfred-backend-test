from django.shortcuts import render
from rest_framework import viewsets, status, generics, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
import math

from .models import Address, Driver, Service, calculate_haversine_distance
from .serializers import (
    AddressSerializer, DriverSerializer, ServiceSerializer, 
    ServiceRequestSerializer, ServiceUpdateSerializer
)



class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer

class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer


class RequestServiceView(APIView):

    def post(self, request, *args, **kwargs):
        request_serializer = ServiceRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        customer_lat = request_serializer.validated_data['latitude']
        customer_lon = request_serializer.validated_data['longitude']

        available_drivers = Driver.objects.filter(is_available=True)
        if not available_drivers.exists():
            return Response({"message": "Conductores no disponibles en este momento."}, status=status.HTTP_404_NOT_FOUND)

        closest_driver = None
        min_distance = float('inf')

        for driver in available_drivers:
            distance = calculate_haversine_distance(
                driver.current_latitude, driver.current_longitude,
                customer_lat, customer_lon
            )
            if distance < min_distance:
                min_distance = distance
                closest_driver = driver
        
        if closest_driver is None:
             return Response({"message": "No se pudo encontrar un conductor adecuado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        average_speed_kph = 40
        estimated_time_hours = min_distance / average_speed_kph
        estimated_arrival = timezone.now() + timedelta(hours=estimated_time_hours)

        service = Service.objects.create(
            customer_pickup_latitude=customer_lat,
            customer_pickup_longitude=customer_lon,
            assigned_driver=closest_driver,
            status=Service.StatusChoices.ASSIGNED,
            estimated_arrival_time=estimated_arrival
        )

        closest_driver.is_available = False
        closest_driver.save()

        service_serializer = ServiceSerializer(service)
        return Response(service_serializer.data, status=status.HTTP_201_CREATED)

class CompleteServiceView(generics.UpdateAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceUpdateSerializer
    lookup_field = 'pk'

    def perform_update(self, serializer):
        service = serializer.instance
        
        if service.status != Service.StatusChoices.ASSIGNED:
            raise serializers.ValidationError({"status": "El servicio debe estar en estado ASIGNADO para ser completado."}, code='invalid_state')
        
        if not service.assigned_driver:
             raise serializers.ValidationError({"driver": "Conductor no asignado a este servicio."}, code='estado_invalido')

        validated_status = serializer.validated_data['status']
        
        service.status = validated_status
        service.completion_time = timezone.now()
        service.save()

        driver = service.assigned_driver
        driver.is_available = True
        driver.save()


    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object() 
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer) 

            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            full_serializer = ServiceSerializer(instance)
            return Response(full_serializer.data)

        except serializers.ValidationError as e:
             return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
