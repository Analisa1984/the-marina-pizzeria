from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import BookingForm, UpdateBookingForm, RegistrationForm
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from .models import Booking, Table
from django import forms
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, User



# Create your views here.


# for index page
def index(request):
    return render(request, 'bookings/index.html', {'title': 'index'})


@login_required # This replaces your 'if not authenticated' check more cleanly
def bookings(request):
    # 1. Start by handling the POST request (when the user clicks "Book Now")
    if request.method == 'POST':
        form_booking = BookingForm(request.POST)
        
        # 2. Check if the form data (date, time, guests) is valid
        if form_booking.is_valid():
                   
            # Extract cleaned data to use for our availability logic
            booking_date = form_booking.cleaned_data['booking_date'] 
            booking_time = form_booking.cleaned_data['booking_time']
            party_number = form_booking.cleaned_data['party_number']

            if booking_date < timezone.now().date():
                messages.error(request, "Ciao! We can't travel back in time. Please pick a future date.")

            # 3. Create a 'datetime' object to allow for easy time math
            requested_datetime = datetime.combine(booking_date, booking_time)
            
            # 4. Get a list of all tables that can fit this many people
            # We order by capacity so we use the smallest appropriate table first
            suitable_tables = Table.objects.filter(seating_capacity__gte=party_number).order_by('seating_capacity')

            assigned_table = None

            # Set a buffer of 1 hour 59 minutes before and after
            start_buffer = (requested_datetime - timedelta(hours=1, minutes=59)).time()
            end_buffer = (requested_datetime + timedelta(hours=1, minutes=59)).time()

            # 5. THE SMART LOOP: Check each table for availability
            for table in suitable_tables:

                # Check if this specific table is already booked in that 4-hour window
                is_occupied = Booking.objects.filter(
                    table_id=table,
                    booking_date=booking_date,
                    booking_time__range=(start_buffer, end_buffer)
                ).exists()

                # If the table is NOT occupied, we've found our winner!
                if not is_occupied:
                    assigned_table = table
                    break  # Stop looking at other tables

            # 6. If we successfully assigned a table, proceed with saving and emails
            if assigned_table:
                booking = form_booking.save(commit=False)
                booking.User_id = request.user
                booking.table_id = assigned_table
                booking.save()
                
                # Format time for the emails
                standard_time = booking_time.strftime('%I:%M %p')
                
                # --- EMAIL TO CUSTOMER ---
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
                    fail_silently=True,
                )

                # --- EMAIL TO ADMIN ---
                admin_msg = (
                    f"New Booking Alert!\n\n"
                    f"User: {request.user.username}\n"
                    f"Table: {assigned_table.table_number}\n"
                    f"Guests: {party_number}\n"
                    f"When: {booking_date} at {standard_time}"
                )
                send_mail(
                    f'NEW BOOKING: {booking_date}',
                    admin_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    ['tronadenison@gmail.com'], 
                    fail_silently=True,
                )

                # 7. Store data in session for the confirmation page
                request.session['booked_data'] = {
                    'booking_date': str(booking_date),
                    'booking_time': str(booking_time),
                    'party_number': party_number,
                    'table_number': assigned_table.table_number
                }
                return redirect('booked')
            
            else:           
                # 8. No tables were free for that time slot
                form_booking.add_error('booking_time', "All tables for this size are occupied for this 2-hour window. Please try a different time.")
    
    # 9. Handle the GET request (when user first visits the page)
    else:
        form_booking = BookingForm()
    
    return render(request, 'bookings/bookings.html', {'form_booking': form_booking})

# for a list of my bookings (past, current, future), this is for the my bookings page
def my_bookings(request):
    today = timezone.now().date()
    
    past_bookings = Booking.objects.filter(User_id=request.user, booking_date__lt=today).order_by('-booking_date')
    current_bookings = Booking.objects.filter(User_id=request.user, booking_date=today)
    future_bookings = Booking.objects.filter(User_id=request.user, booking_date__gt=today).order_by('booking_date')

    # This is the key: instantiate the form to pass it to the context
    form = UpdateBookingForm()

    context = {
        'past_bookings': past_bookings,
        'current_bookings': current_bookings,
        'future_bookings': future_bookings,
        'form': form, # Now the template can see the dropdown options
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
@login_required
def update_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, User_id=request.user)
    
    if request.method == "POST":
        form = UpdateBookingForm(request.POST, instance=booking)
        
        if form.is_valid():
            new_date = form.cleaned_data['booking_date']
            #  Prevents guests from updating to a past date
            if new_date < timezone.now().date():
                messages.error(request, "You cannot update a booking to a past date.")
                return redirect('my_bookings')

            time_data = form.cleaned_data['booking_time'] # This is the string from the dropdown
            
            # --- THE FIX: Convert string to datetime.time object ---
            if isinstance(time_data, str):
                # 'H:M' matches '12:00', '13:30', etc.
                new_time = datetime.strptime(time_data, '%H:%M').time()
            else:
                new_time = time_data
            # -------------------------------------------------------

            new_party = int(form.cleaned_data['party_number'])
            
            # Now this will work because new_time is a time object, not a string!
            requested_dt = datetime.combine(new_date, new_time)
            
            # ... rest of your buffer logic ...
            buffer = timedelta(hours=1, minutes=59)
            start_buffer = (requested_dt - buffer).time()
            end_buffer = (requested_dt + buffer).time()

            suitable_tables = Table.objects.filter(seating_capacity__gte=new_party).order_by('seating_capacity')
            
            assigned_table = None
            for table in suitable_tables:
                is_occupied = Booking.objects.filter(
                    table_id=table,
                    booking_date=new_date,
                    booking_time__range=(start_buffer, end_buffer)
                ).exclude(booking_id=booking_id).exists()

                if not is_occupied:
                    assigned_table = table
                    break

            if assigned_table:
                updated_booking = form.save(commit=False)
                updated_booking.booking_time = new_time # Ensure object is saved
                updated_booking.table_id = assigned_table
                updated_booking.save()
                messages.success(request, "Booking updated successfully!")
            else:
                messages.error(request, "No tables available for this time.")
        else:
            messages.error(request, "Invalid data.")
            
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
                fail_silently=True,
            )

            # EMAIL B: To You (The Admin Notification)
            send_mail(
                subject=f'NEW CONTACT FORM: {name}',
                message=f'New inquiry received from {name} ({user_email}):\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['tronadenison@gmail.com'], # Replace with your real email
                fail_silently=True,
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
            return redirect('login_redirect')
    else:
        form = AuthenticationForm()
    return render(request, 'bookings/login.html', {'form':form, 'title':'log in'})

@login_required
def login_redirect(request):
    """
    Step 1: The 'Traffic Cop' check.
    As soon as someone logs in, this function runs.
    """
    # Look for the 'Staff' group badge
    if request.user.groups.filter(name='Staff').exists() or request.user.is_staff:
        # Success! Teleport to the Portal
        return redirect('staff_portal')
    else:
        # Regular customer? Send them to their bookings
        return redirect('my_bookings')

@login_required
def staff_portal_view(request):
    """
    Step 2: The actual Portal page.
    This just opens the 'staff_portal.html' file you built.
    """
    # Security check: If a sneaky customer types /staff-portal/ manually, 
    # we kick them out.
    if not request.user.groups.filter(name='Staff').exists() and not request.user.is_staff:
        messages.error(request, "Access denied. Staff only area!")
        return redirect('index')
        
    return render(request, 'bookings/staff_portal.html')

@login_required
def staff_register_customer(request):
    """
    This view allows a staff member to create a new user account 
    for a customer who is standing in front of them or on the phone.
    """
    # Security: Kick out anyone who isn't staff
    if not request.user.groups.filter(name='Staff').exists() and not request.user.is_staff:
        messages.error(request, "You do not have permission to register customers.")
        return redirect('index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # 1. Save the new user
            new_user = form.save()
            
            # 2. Automatically put them in the 'Customer' group
            customer_group, created = Group.objects.get_or_create(name='Customer')
            new_user.groups.add(customer_group)
            
            messages.success(request, f"Success! Account created for {new_user.username}.")
            return redirect('staff_portal') # Send staff back to their command center
    else:
        form = UserCreationForm()

    return render(request, 'bookings/staff_register.html', {'form': form})


@login_required
def staff_dashboard_view(request):
    if not request.user.groups.filter(name='Staff').exists() and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('index')

    # Get today's date to help with highlighting
    today = timezone.now().date()
    
    # Grab everything, sorted so the most recent dates are at the top
    all_bookings = Booking.objects.all().order_by('booking_date', 'booking_time')

    return render(request, 'bookings/staff_dashboard.html', {
        'all_bookings': all_bookings,
        'today': today
    })

