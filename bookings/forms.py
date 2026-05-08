from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Booking

class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone_no = forms.CharField(max_length = 20)
    first_name = forms.CharField(max_length = 20)
    last_name = forms.CharField(max_length = 20)
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_no', 'password1', 'password2']


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['party_number', 'booking_date', 'booking_time']
        widgets = {
             'booking_date': forms.DateInput(attrs={'type': 'date'}),
             'booking_time': forms.TimeInput(attrs={'type': 'time'}),
    } 

    # Logic involving multiple fields
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time = cleaned_data.get('booking_time')
        
        if booking_date and booking_time:
            # Combine date and time into a single datetime object
            booking_datetime = datetime.combine(booking_date, booking_time)

        return cleaned_data


