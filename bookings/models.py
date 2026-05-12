from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

STATUS = ((0, 'Pending'), (1, 'Confirmed'), (2, 'Cancelled'), (3, 'Completed'))
USER_TYPE = ((0, 'Patron'), (1, 'Staff'))

# Create your models here.
class Booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    User_id = models.ForeignKey(User, on_delete=models.CASCADE)
    table_id = models.ForeignKey('Table', on_delete=models.CASCADE)
    party_number = models.PositiveIntegerField(blank=False, validators=[MinValueValidator(1), MaxValueValidator(20)])
    booking_date = models.DateField(blank=False)
    booking_time = models.TimeField(blank=False)
    created_on = models.DateTimeField(auto_now_add=True)
    status = models.PositiveIntegerField(choices=STATUS, default=0)


    class Meta:
        ordering = ['booking_date', 'booking_time']
    

    def __str__(self):
        return f"Booking for {self.User_id.first_name} {self.User_id.last_name} on {self.booking_date} at {self.booking_time} for {self.party_number} people."
    


class Table(models.Model):
    table_id = models.AutoField(primary_key=True)
    table_number = models.PositiveIntegerField(validators=[MinValueValidator(20), MaxValueValidator(30)], blank=False)
    seating_capacity = models.PositiveIntegerField(blank=False)

    def __str__(self):
        return f"Table {self.table_number} (Seats {self.seating_capacity})"
