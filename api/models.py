from django.db import models
import math

class Address(models.Model):
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self) -> str:
        return f"{self.street_address}, {self.city}"

class Driver(models.Model):
    name = models.CharField(max_length=100)
    current_latitude = models.FloatField()
    current_longitude = models.FloatField()
    is_available = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name}"

class Service(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    customer_pickup_latitude = models.FloatField()
    customer_pickup_longitude = models.FloatField()


    assigned_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services'
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    request_time = models.DateTimeField(auto_now_add=True)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Service {self.pk} - {self.status}"


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    return c * r


