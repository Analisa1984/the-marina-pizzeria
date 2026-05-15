from datetime import time, date
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Booking
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column

# Set Time Choices for 30 minute invervals between noon and 11pm
# This is Global as its for all Time selectors
TIME_CHOICES = [
    (
        time(hour, minute).strftime('%H:%M'),
        time(hour, minute).strftime('%H:%M')
    )
    for hour in range(12, 23)
    for minute in (0, 30)
]

# Set party size to 10 for all party size selectors
PARTY_SIZE_CHOICES = [(i, str(i)) for i in range(1, 11)]


class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=20)
    last_name = forms.CharField(max_length=20)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']


class BookingForm(forms.ModelForm):
    booking_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    party_number = forms.ChoiceField(
        choices=PARTY_SIZE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Number of Guests"
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time_str = cleaned_data.get('booking_time')
        party_number = cleaned_data.get('party_number')

        if booking_date and booking_time_str:
            try:
                hour, minute = map(int, booking_time_str.split(':'))
                booking_time = time(hour, minute)
            except (ValueError, AttributeError):
                # If the time is missing, stop here
                raise ValidationError("Please select a valid booking time.")

            if booking_date.weekday() == 6:
                raise ValidationError(
                    "The Marina Pizzeria is closed on Sundays."
                )

            if 0 <= booking_date.weekday() <= 3:
                opening, closing = time(12, 0), time(22, 0)
            else:
                opening, closing = time(12, 0), time(23, 0)

            if booking_time < opening or booking_time > closing:
                raise ValidationError(
                    f"We are only open from {opening.strftime('%H:%M')}"
                    f"to {closing.strftime('%H:%M')} on this day."
                )

            cleaned_data['booking_time'] = booking_time

        if not booking_date:
            return cleaned_data

        if booking_date < date.today():
            raise forms.ValidationError(
                "You cannot book a table in the past."
            )
        if booking_date and booking_time_str:
            try:
                hour, minute = map(int, booking_time_str.split(':'))
                booking_time = time(hour, minute)
            except (ValueError, AttributeError):
                raise ValidationError("Please select a valid booking time.")

        if party_number:
            cleaned_data['party_number'] = int(party_number)

        return cleaned_data


class UpdateBookingForm(forms.ModelForm):
    booking_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    party_number = forms.ChoiceField(
        choices=PARTY_SIZE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Number of Guests"
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'booking_time', 'party_number']
        widgets = {
            'booking_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the initial dropdown value to the existing booking time
        if self.instance and self.instance.booking_time:
            self.initial['booking_time'] = self.instance.booking_time.strftime(
                '%H:%M'
            )
            self.initial['party_number'] = self.instance.party_number

        # Keep the Crispy Forms layout
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('booking_date', css_class='form-group col-md-6 mb-0'),
                Column('booking_time', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'party_number',
            Submit(
                'submit', 'Update Booking', css_class='btn btn-success mt-3'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        booking_time_str = cleaned_data.get('booking_time')
        party_number = cleaned_data.get('party_number')

        if booking_date and booking_time_str:
            try:
                if isinstance(booking_time_str, str):
                    hour, minute = map(int, booking_time_str.split(':'))
                    booking_time = time(hour, minute)
                else:
                    booking_time = booking_time_str

                # Pizzeria opening hours logic (exclude Sunday)
                if booking_date.weekday() == 6:
                    raise ValidationError(
                        "The Marina Pizzeria is closed on Sundays."
                    )

                if 0 <= booking_date.weekday() <= 3:
                    opening, closing = time(12, 0), time(22, 0)
                else:
                    opening, closing = time(12, 0), time(23, 0)

                if booking_time < opening or booking_time > closing:
                    raise ValidationError(
                        f"We are only open from {opening.strftime('%H:%M')}"
                        f"to {closing.strftime('%H:%M')} on this day."
                    )

                cleaned_data['booking_time'] = booking_time
            except (ValueError, AttributeError):
                raise ValidationError("Invalid time format selected.")

        if party_number:
            cleaned_data['party_number'] = int(party_number)

        return cleaned_data


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-3',
            'placeholder': 'Your Full Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control rounded-3',
            'placeholder': 'email@example.com'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control rounded-3',
            'placeholder': 'How can we help you today?',
            'rows': 5
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = True


class StaffBookingForm(BookingForm):
    # Select the customer from all registered users
    customer = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    booking_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Booking Time"
    )

    party_number = forms.ChoiceField(
        choices=PARTY_SIZE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Number of Guests"
    )

    class Meta(BookingForm.Meta):
        fields = ['customer', 'booking_date', 'booking_time', 'party_number']
