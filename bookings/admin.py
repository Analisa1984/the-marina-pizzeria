from django.contrib import admin
from bookings.models import Booking
from bookings.models import Table

# Register your models here.
admin.site.register(Booking)
admin.site.register(Table)
