from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import BookingForm, UpdateBookingForm, RegistrationForm
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from .models import Booking, Table
from django import forms
from .forms import BookingForm
from django.utils import timezone
from django.conf import settings

# Create your views here.


# for index page
def index(request):
    return render(request, 'bookings/index.html', {'title': 'index'})


def bookings(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form_booking = BookingForm(request.POST)
        if form_booking.is_valid():
            booking = form_booking.save(commit=False)
            booking.User_id = request.user
            party_number = form_booking.cleaned_data['party_number']
            booking_date = form_booking.cleaned_data['booking_date'] 
            booking_time = form_booking.cleaned_data['booking_time']
            standard_time = booking_time.strftime('%I:%M %p')
            suitable_tables = Table.objects.filter(seating_capacity__gte=party_number).order_by('seating_capacity').first()
            if suitable_tables:
                # We found a table! suitable_table.id is what you need.
                booking.table_id = suitable_tables
                booking.save()
                
                # 1. Email to the Customer
                customer_msg = (
                    f"Ciao {request.user.username}!\n\n"
                    f"Your table at The Marina Pizzeria is confirmed.\n"
                    f"Date: {booking_date}\n"
                    f"Time: {standard_time}\n"
                    f"Party Size: {party_number}\n\n"
                    f"We look forward to seeing you!"
                )
                
                send_mail(
                    'Booking Confirmed! 🍕',
                    customer_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False,
                )

                # 2. Email to the Admin (You)
                admin_msg = (
                    f"New Booking Alert!\n\n"
                    f"User: {request.user.username}\n"
                    f"Table: {suitable_tables.table_number}\n"
                    f"Guests: {party_number}\n"
                    f"When: {booking_date} at {standard_time}"
                )

                send_mail(
                    f'NEW BOOKING: {booking_date}',
                    admin_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    ['tronadenison@gmail.com'], 
                    fail_silently=False,
                )

                request.session['booked_data'] = {
                'booking_date': str(form_booking.cleaned_data['booking_date']), # Convert date to string
                'booking_time': str(form_booking.cleaned_data['booking_time']), # Convert time to string
                'party_number': form_booking.cleaned_data['party_number'],
                'table_number': suitable_tables.table_number if suitable_tables else "None"
            }
                return redirect('booked')
            else:           
                # No table large enough was found
                form_booking.add_error('party_number', "No tables available for this many guests.")
    else:
        form_booking = BookingForm()
    
    return render(request, 'bookings/bookings.html', {'form_booking': form_booking})

# for a list of my bookings (past, current, future), this is for the my bookings page
def my_bookings(request):
    today = timezone.now().date()
    
    # Filter bookings based on the current date
    past_bookings = Booking.objects.filter(User_id=request.user, booking_date__lt=today).order_by('-booking_date', '-booking_time')
    current_bookings = Booking.objects.filter(User_id=request.user, booking_date=today)
    future_bookings = Booking.objects.filter(User_id=request.user, booking_date__gt=today).order_by('-booking_date', '-booking_time')

    context = {
        'past_bookings': past_bookings,
        'current_bookings': current_bookings,
        'future_bookings': future_bookings,
    }
    return render(request, 'bookings/my_bookings.html', context)

# for cancelling the bookings made by user

def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, User_id=request.user)
    if request.method == "POST":
        booking.delete()
        messages.success(request, "Booking cancelled successfully.")
        return redirect('my_bookings') 
    return redirect('my_bookings')


# for editing the bookings made by user
def update_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, User_id=request.user)
    
    if request.method == "POST":
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            booking_date = form.cleaned_data['booking_date']
            booking_time = form.cleaned_data['booking_time']
            new_party_size = form.cleaned_data['party_number']
            standard_time = booking_time.strftime('%I:%M %p')
            
            # Check table capacity
            if new_party_size > booking.table_id.seating_capacity:
                suitable_table = Table.objects.filter(seating_capacity__gte=new_party_size).first()
                if suitable_table:
                    booking.table_id = suitable_table
                else:
                    messages.error(request, f"Could not update: No tables available for {new_party_size} guests.")
                    return redirect('my_bookings')
            
            form.save()
           
            send_mail(
                subject="Your Booking at The Marina has been Updated! 🍕",
                message=(
                    f"Ciao {request.user.username},\n\n"
                    f"Your booking has been successfully updated.\n"
                    f"New Details:\n"
                    f"Date: {booking_date}\n"
                    f"Time: {standard_time}\n"  
                    f"Party Size: {new_party_size}\n\n"
                    f"See you then!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
            )

            messages.success(request, "Booking updated successfully! Confirmation email sent.")
        else:
            messages.error(request, "There was an error in your update. Please check the details.")
            
    return redirect('my_bookings')  


# for menu page
def menu(request):
    return render(request, 'bookings/menu.html', {'title': 'menu'})

# for about page
def about(request):
    return render(request, 'bookings/about.html', {'title': 'about'})

# for contact us
class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        if form.is_valid():
            # Extract cleaned data
            name = form.cleaned_data['name']
            user_email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # EMAIL A: To the Customer (The "Grazie" email)
            send_mail(
                subject='Thank You, from The Marina Pizzeria!',
                message=f'Hello {name},\n\nWe received your message: "{message}". Our team will be in touch shortly!\n\nBest,\nThe Marina Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False,
            )

            # EMAIL B: To You (The Admin Notification)
            send_mail(
                subject=f'NEW CONTACT FORM: {name}',
                message=f'New inquiry received from {name} ({user_email}):\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['tronadenison@gmail.com'], # Replace with your real email
                fail_silently=False,
            )

            # Return the page with success=True
            return render(request, 'bookings/contact.html', {
                'form': ContactForm(),  # Reset to a blank form
                'success': True,
                'title': 'Thank You',
                'user': request.user   # Keeps the username fix active
            })
            
    else:
        # Initial visit to the page
        form = ContactForm()

    return render(request, 'bookings/contact.html', {
        'form': form, 
        'title': 'Contact Us',
        'user': request.user
    })

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
            htmly = get_template('bookings/email.html')
            d = { 'username': username }
            subject, from_email, to = 'welcome', 'tronadenison@gmail.com', email
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
        form = AuthenticationForm(request, data=request.POST) # Better to use the form class
        if form.is_valid():
            user = form.get_user()
            login(request, user) # Just call it
            messages.success(request, f' Hello, {user.username} !!')
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'bookings/login.html', {'form':form, 'title':'log in'})

