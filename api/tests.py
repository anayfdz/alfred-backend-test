from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from faker import Faker
import math
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from .models import Driver, Service, Address, calculate_haversine_distance
from .serializers import ServiceSerializer 



class ModelTests(TestCase):

    def setUp(self):
        self.fake = Faker()
        self.driver = Driver.objects.create(
            name="Test Driver", 
            current_latitude=40.7128, 
            current_longitude=-74.0060, # NYC
            is_available=True
        )
        self.service = Service.objects.create(
            customer_pickup_latitude=40.7580, # Times Square
            customer_pickup_longitude=-73.9855,
            assigned_driver=self.driver,
            status=Service.StatusChoices.ASSIGNED
        )
        self.address = Address.objects.create(
            street_address=self.fake.street_address(),
            city=self.fake.city(),
            state=self.fake.state_abbr(),
            postal_code=self.fake.postcode(),
            latitude=self.fake.latitude(),
            longitude=self.fake.longitude()
        )

    def test_driver_str(self):
        self.assertEqual(str(self.driver), "Test Driver")

    def test_service_str(self):
        self.assertEqual(str(self.service), f"Service {self.service.pk} - ASSIGNED")

    def test_address_str(self):
        expected_str = f"{self.address.street_address}, {self.address.city}"
        self.assertEqual(str(self.address), expected_str)

    def test_haversine_calculation(self):
        # (aprox de NYC a Times Square)
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7580, -73.9855
        expected_distance_km = 5.3 # Aproximado
        calculated_distance = calculate_haversine_distance(lat1, lon1, lat2, lon2)
        self.assertAlmostEqual(calculated_distance, expected_distance_km, delta=0.5)


class AuthenticatedAPITestCase(APITestCase):
    """Base class for API tests that require authentication."""
    def setUp(self):
        # Crear usuario de prueba
        self.test_user = User.objects.create_user(
            username='testuser', 
            password='testpassword123'
        )
        # Generar token para el usuario de prueba
        self.token = Token.objects.create(user=self.test_user)
        # Setear el token en las credenciales del cliente
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

class ServiceAPITests(AuthenticatedAPITestCase):

    def setUp(self):
        super().setUp()
        # Create conductores de prueba
        self.driver1 = Driver.objects.create(name="Driver One", current_latitude=10.0, current_longitude=10.0, is_available=True)
        self.driver2 = Driver.objects.create(name="Driver Two", current_latitude=50.0, current_longitude=50.0, is_available=True)
        self.driver3 = Driver.objects.create(name="Driver Three", current_latitude=10.1, current_longitude=10.1, is_available=False) # Unavailable

    def test_request_service_success(self):
        """Test requesting a service finds the nearest available driver."""
        url = reverse('request-service')
        # Localización del cliente cerca del conductor 1
        data = {"latitude": 10.01, "longitude": 10.01}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Service.objects.count(), 1)
        service = Service.objects.first()
        self.assertEqual(service.assigned_driver, self.driver1)
        self.assertEqual(service.status, Service.StatusChoices.ASSIGNED)
        self.assertIsNotNone(service.estimated_arrival_time)
        
        # Verificar que el conductor 1 no esté disponible
        self.driver1.refresh_from_db()
        self.assertFalse(self.driver1.is_available)

    def test_request_service_no_available_drivers(self):
        """Test requesting a service when no drivers are available."""
        # Marcar todos los conductores como no disponibles
        Driver.objects.update(is_available=False)
        
        url = reverse('request-service')
        data = {"latitude": 20.0, "longitude": 20.0}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Service.objects.count(), 0)
        self.assertIn("No available drivers", response.data['message'])

    def test_request_service_invalid_coordinates(self):
        """Test requesting a service with invalid latitude/longitude."""
        url = reverse('request-service')
        data = {"latitude": 95.0, "longitude": -200.0} # Invalida log/lat
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)
        self.assertIn('longitude', response.data)
        self.assertEqual(Service.objects.count(), 0)

    def test_complete_service_success(self):
        """Test marking an assigned service as completed."""
        # Crear un servicio asignado
        service = Service.objects.create(
            customer_pickup_latitude=30.0, 
            customer_pickup_longitude=30.0,
            assigned_driver=self.driver2,
            status=Service.StatusChoices.ASSIGNED
        )
        self.driver2.is_available = False # El conductor se vuelve no disponible
        self.driver2.save()

        url = reverse('complete-service', kwargs={'pk': service.pk})
        data = {"status": "COMPLETED"} # Enviar el estado requerido
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.refresh_from_db()
        self.assertEqual(service.status, Service.StatusChoices.COMPLETED)
        self.assertIsNotNone(service.completion_time)
        
        # Verificar que el conductor esté disponible de nuevo
        self.driver2.refresh_from_db()
        self.assertTrue(self.driver2.is_available)

    def test_complete_service_invalid_status_update(self):
        """Test trying to mark a service with a status other than COMPLETED via the endpoint."""
        service = Service.objects.create(customer_pickup_latitude=30.0, customer_pickup_longitude=30.0, assigned_driver=self.driver2, status=Service.StatusChoices.ASSIGNED)
        url = reverse('complete-service', kwargs={'pk': service.pk})
        data = {"status": "PENDING"} # Estado inválido para este endpoint
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Can only update status to COMPLETED', str(response.data))
        service.refresh_from_db()
        self.assertEqual(service.status, Service.StatusChoices.ASSIGNED) # El estado no debería cambiar

    def test_complete_service_not_assigned(self):
        """Test trying to complete a service that is not in ASSIGNED state."""
        service = Service.objects.create(customer_pickup_latitude=30.0, customer_pickup_longitude=30.0, status=Service.StatusChoices.PENDING) # No asignado
        url = reverse('complete-service', kwargs={'pk': service.pk})
        data = {"status": "COMPLETED"}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Service must be in ASSIGNED state', str(response.data))
        service.refresh_from_db()
        self.assertEqual(service.status, Service.StatusChoices.PENDING) # El estado no debería cambiar

    def test_complete_service_not_found(self):
        """Test trying to complete a service that does not exist."""
        non_existent_pk = 9999
        url = reverse('complete-service', kwargs={'pk': non_existent_pk})
        data = {"status": "COMPLETED"}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DriverViewSetTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.driver1 = Driver.objects.create(name="Driver A", current_latitude=1.0, current_longitude=1.0)
        self.list_url = reverse('driver-list') # Nota: Nombres de rutas del router de DRF por defecto
        self.detail_url = reverse('driver-detail', kwargs={'pk': self.driver1.pk})

    def test_list_drivers(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_driver(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Driver A")

    def test_create_driver(self):
        data = {"name": "Driver B", "current_latitude": 2.0, "current_longitude": 2.0, "is_available": False}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Driver.objects.count(), 2)
        self.assertEqual(response.data['name'], "Driver B")

    def test_update_driver(self):
        data = {"name": "Driver A Updated", "current_latitude": 1.1, "current_longitude": 1.1, "is_available": False}
        response = self.client.put(self.detail_url, data, format='json') # PUT para actualización parcial
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.driver1.refresh_from_db()
        self.assertEqual(self.driver1.name, "Driver A Updated")
        self.assertFalse(self.driver1.is_available)

    def test_partial_update_driver(self):
        data = {"is_available": False}
        response = self.client.patch(self.detail_url, data, format='json') 
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.driver1.refresh_from_db()
        self.assertFalse(self.driver1.is_available)
        self.assertEqual(self.driver1.name, "Driver A") # No debería cambiar el nombre

    def test_delete_driver(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Driver.objects.count(), 0)
