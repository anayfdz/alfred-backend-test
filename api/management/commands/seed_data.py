import random
from django.core.management.base import BaseCommand
from faker import Faker
from api.models import Address, Driver

class Command(BaseCommand):
    help = 'Seeds the database with fake addresses and drivers'

    def handle(self, *args, **options):
        fake = Faker()
        
        self.stdout.write('Clearing existing Address and Driver data...')
        Address.objects.all().delete()
        Driver.objects.all().delete()

        addresses = []
        address_count = 25 
        self.stdout.write(f'Seeding {address_count} addresses...')
        for _ in range(address_count):
            address = Address(
                street_address=fake.street_address(),
                city=fake.city(),
                state=fake.state_abbr(),
                postal_code=fake.postcode(),
                latitude=fake.latitude(),
                longitude=fake.longitude()
            )
            addresses.append(address)
        Address.objects.bulk_create(addresses)
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {address_count} addresses.'))

        drivers = []
        driver_count = 25
        self.stdout.write(f'Seeding {driver_count} drivers...')
        for _ in range(driver_count):
            driver = Driver(
                name=fake.name(),
                current_latitude=fake.latitude(),
                current_longitude=fake.longitude(),
                is_available=random.choice([True, True, True, False]) 
            )
            drivers.append(driver)
        Driver.objects.bulk_create(drivers)
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {driver_count} drivers.'))

        self.stdout.write(self.style.SUCCESS('Database seeding complete.')) 