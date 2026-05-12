from datetime import time, date
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Booking
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

# 1. Choices for Time and Party Size
TIME_CHOICES = [
    (time(hour, minute).strftime('%H:%M'), time(hour, minute).strftime('%H:%M'))
    for hour in range(12, 23) 
    for minute in (0, 30)
]

PARTY_SIZE_CHOICES = [(i, str(i)) for i in range(1, 11)]

class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone_no = forms.CharField(max_length=20)
    first_name = forms.CharField(max_length=20)
    last_name = forms.CharField(max_length=20)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_no', 'first_name', 'last_name']

class BookingForm(forms.ModelForm):
    # Time dropdown (30 min intervals)
    booking_time = forms.ChoiceField( 
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # NEW: Party size dropdown (1-10)
    party_number = forms.ChoiceField(
        choices=PARTY_SIZE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Number of Guests"
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time_str = cleaned_data.get('booking_time')
        # Ensure party_number is treated as an integer
        party_number = cleaned_data.get('party_number')

        if booking_date and booking_time_str:
            hour, minute = map(int, booking_time_str.split(':'))
            booking_time = time(hour, minute)

            if booking_date.weekday() == 6:
                raise ValidationError("The Marina Pizzeria is closed on Sundays.")

            if 0 <= booking_date.weekday() <= 3: # Mon-Thu
                opening, closing = time(12, 0), time(22, 0)
            else: # Fri-Sat
                opening, closing = time(12, 0), time(23, 0)
            
            if booking_time < opening or booking_time > closing:
                raise ValidationError(f"We are only open from {opening.strftime('%H:%M')} to {closing.strftime('%H:%M')} on this day.")
            
            cleaned_data['booking_time'] = booking_time
        
        if booking_date < date.today():
            raise forms.ValidationError("Time travel hasn't been invented yet! You cannot book a table in the past.")
        
        if party_number:
            cleaned_data['party_number'] = int(party_number)

        return cleaned_data
    
    
class UpdateBookingForm(forms.ModelForm):
    # Ensuring the update form also uses the dropdowns for consistency
    booking_time = forms.ChoiceField(choices=TIME_CHOICES, widget=forms.Select())
    party_number = forms.ChoiceField(choices=PARTY_SIZE_CHOICES, widget=forms.Select())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('booking_date', css_class='form-group col-md-6 mb-0'),
                Column('booking_time', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'party_number',
            Submit('submit', 'Update Booking', css_class='btn btn-success mt-3')
        )

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time_str = cleaned_data.get('booking_time')
        # Ensure party_number is treated as an integer
        party_number = cleaned_data.get('party_number')

        if booking_date and booking_time_str:
            hour, minute = map(int, booking_time_str.split(':'))
            booking_time = time(hour, minute)

            if booking_date.weekday() == 6:
                raise ValidationError("The Marina Pizzeria is closed on Sundays.")

            if 0 <= booking_date.weekday() <= 3: # Mon-Thu
                opening, closing = time(12, 0), time(22, 0)
            else: # Fri-Sat
                opening, closing = time(12, 0), time(23, 0)
            
            if booking_time < opening or booking_time > closing:
                raise ValidationError(f"We are only open from {opening.strftime('%H:%M')} to {closing.strftime('%H:%M')} on this day.")
            
            cleaned_data['booking_time'] = booking_time
        
        if party_number:
            cleaned_data['party_number'] = int(party_number)

        return cleaned_data

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
        }