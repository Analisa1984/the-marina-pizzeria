from urllib import request

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import BookingForm, RegistrationForm
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from .models import Booking, Table
from django import forms
from .forms import BookingForm

# Create your views here.
#def my_bookings(request):
#    return HttpResponse("This is the bookings page.")

# for index page
def index(request):
    return render(request, 'bookings/index.html', {'title': 'index'})

def bookings(request):
    if request.method == 'POST':
        form_booking = BookingForm(request.POST)
        if form_booking.is_valid():
            booking = form_booking.save(commit=False)
            booking.User_id = request.user
            party_number = form_booking.cleaned_data['party_number']
            suitable_tables = Table.objects.filter(seating_capacity__gte=party_number).order_by('seating_capacity').first()
            if suitable_tables:
                # We found a table! suitable_table.id is what you need.
                booking.table_id = suitable_tables
            else:
                # No table large enough was found
                form_booking.add_error('party_number', "No tables available for this many guests.")
            booking.save()
            
            request.session['booked_data'] = {
                'booking_date': str(form_booking.cleaned_data['booking_date']), # Convert date to string
                'booking_time': str(form_booking.cleaned_data['booking_time']), # Convert time to string
                'party_number': form_booking.cleaned_data['party_number'],
                'table_number': suitable_tables.table_number if suitable_tables else "None"
            }

            return redirect('booked')
    else:
        form_booking = BookingForm()
    
    return render(request, 'bookings/bookings.html', {'form_booking': form_booking})

# for menu page
def menu(request):
    return render(request, 'bookings/menu.html', {'title': 'menu'})

# for about page
def about(request):
    return render(request, 'bookings/about.html', {'title': 'about'})

# for contact page
def contact(request):
    return render(request, 'bookings/contact.html', {'title': 'contact'})

# for booked page
def booked(request):
    booked_data = request.session.get('booked_data')
    return render(request, 'bookings/booked.html', {'title': 'booked', 'booked_data': booked_data})

# for registration page
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            phone_no = form.cleaned_data.get('phone_no')
            htmly = get_template('bookings/Email.html')
            d = { 'username': username }
            subject, from_email, to = 'welcome', 'your_email@gmail.com', email
            html_content = htmly.render(d)
            msg = EmailMultiAlternatives(subject, html_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            messages.success(request, f'Account created for {username}! You can now Log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'bookings/register.html', {'form': form, 'title': 'register here'}) 

# for login page
def Login(request):
    if request.method == 'POST':
 
        # AuthenticationForm_can_also_be_used__
 
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username = username, password = password)
        if user is not None:
            form = login(request, user)
            messages.success(request, f' Hello, {username} !!')
            return redirect('index')
        else:
            messages.info(request, f'account done not exit plz sign in')
    form = AuthenticationForm()
    return render(request, 'bookings/login.html', {'form':form, 'title':'log in'}) 

