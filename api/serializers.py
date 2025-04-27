from rest_framework import serializers
from .models import Address, Driver, Service

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    assigned_driver = DriverSerializer(read_only=True)

    class Meta:
        model = Service
        fields = (
            'id', 'customer_pickup_latitude', 'customer_pickup_longitude',
            'assigned_driver', 'status', 'request_time', 
            'estimated_arrival_time', 'completion_time'
        )
        read_only_fields = (
            'id', 'assigned_driver', 'status', 'request_time', 
            'estimated_arrival_time', 'completion_time'
        )

class ServiceRequestSerializer(serializers.Serializer):
    """Serializer for incoming service requests."""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    def validate(self, data):
        errors = {}
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude is None:
            errors['latitude'] = "This field is required."
        elif not (-90 <= latitude <= 90):
            errors['latitude'] = "Latitude must be between -90 and 90."
        
        if longitude is None:
             errors['longitude'] = "This field is required."
        elif not (-180 <= longitude <= 180):
            errors['longitude'] = "Longitude must be between -180 and 180."

        if errors:
            raise serializers.ValidationError(errors)
            
        return data

class ServiceUpdateSerializer(serializers.ModelSerializer):
    """Serializer specifically for updating service status (e.g., completing)."""
    class Meta:
        model = Service
        fields = ['status']

    def validate_status(self, value):
        if value != Service.StatusChoices.COMPLETED:
             raise serializers.ValidationError(f"Can only update status to {Service.StatusChoices.COMPLETED} via this endpoint.")
        return value 