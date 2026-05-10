from datetime import time
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Booking
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    phone_no = forms.CharField(max_length = 20)
    first_name = forms.CharField(max_length = 20)
    last_name = forms.CharField(max_length = 20)
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_no', 'password1', 'password2']

# booking form with time in 30minute intervals

TIME_CHOICES = [
    (time(hour, minute).strftime('%H:%M'), time(hour, minute).strftime('%H:%M'))
    for hour in range(12, 23) 
    for minute in (0, 30)
]

class BookingForm(forms.ModelForm):
    
    booking_time = forms.ChoiceField( 
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'party_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time_str = cleaned_data.get('booking_time')

        if booking_date and booking_time_str:
            # Convert the string from the drop-down into a real Python time object
            hour, minute = map(int, booking_time_str.split(':'))
            booking_time = time(hour, minute)

            # Sunday check
            if booking_date.weekday() == 6:
                raise ValidationError("The Marina Pizzeria is closed on Sundays.")

            # Hour logic - Use time() directly now
            if 0 <= booking_date.weekday() <= 3: # Mon-Thu
                opening, closing = time(12, 0), time(22, 0)
            else: # Fri-Sat
                opening, closing = time(12, 0), time(23, 0)
            
            if booking_time < opening or booking_time > closing:
                raise ValidationError(f"We are only open from {opening.strftime('%H:%M')} to {closing.strftime('%H:%M')} on this day.")
            cleaned_data['booking_time'] = booking_time

        return cleaned_data
    
# form for updating bookings page 
class UpdateBookingForm(forms.ModelForm):
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

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'booking_time': forms.TimeInput(attrs={'type': 'time'}),
        }



