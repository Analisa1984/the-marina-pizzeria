from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import BookingForm, UpdateBookingForm, RegistrationForm, StaffBookingForm, ContactForm
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
from django.contrib.admin.views.decorators import staff_member_required


def index(request):
    return render(request, 'bookings/index.html', {'title': 'index'})

# function for guests to make their own bookings
@login_required 
def bookings(request):
    if request.method == 'POST':
        form_booking = BookingForm(request.POST)
        
        if form_booking.is_valid():
                   
            booking_date = form_booking.cleaned_data['booking_date'] 
            booking_time = form_booking.cleaned_data['booking_time']
            party_number = form_booking.cleaned_data['party_number']

            if booking_date < timezone.now().date():
                messages.error(request, "Oops You Made an Error there lol! We can't travel back in time. Please pick a future date.")

            requested_datetime = datetime.combine(booking_date, booking_time)

        # this will check the table capacity to assign to guest with party number
            suitable_tables = Table.objects.filter(seating_capacity__gte=party_number).order_by('seating_capacity')
            assigned_table = None

            # buffer of 1 hour 59 minutes before and after
            start_buffer = (requested_datetime - timedelta(hours=1, minutes=59)).time()
            end_buffer = (requested_datetime + timedelta(hours=1, minutes=59)).time()
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
                
                # Email to Customer
                customer_msg = (
                    f"Hi there, {request.user.username}!\n\n"
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

                # Email to Admin
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
                    ['themarinapizzeria@gmail.com'],
                    fail_silently=True,
                )

                # Store data in session for the confirmation page
                request.session['booked_data'] = {
                    'booking_date': str(booking_date),
                    'booking_time': str(booking_time),
                    'party_number': party_number,
                    'table_number': assigned_table.table_number
                }
                return redirect('booked')

            else:    
                # No tables free for that time slot
                form_booking.add_error('booking_time', "All tables for this size are occupied for this 2-hour window. Please try a different time.")

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
        'form': form,
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
                messages.error(request, "Time travel hasn't been invented yet! You cannot book a table in the past.")
                return redirect('my_bookings')

            time_data = form.cleaned_data['booking_time'] 
            if isinstance(time_data, str):
                # 'H:M' matches '12:00', '13:30', etc.
                new_time = datetime.strptime(time_data, '%H:%M').time()
            else:
                new_time = time_data

            new_party = int(form.cleaned_data['party_number'])
            requested_dt = datetime.combine(new_date, new_time)
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
                updated_booking.booking_time = new_time
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

            # EMAIL A: To the Customer (The thank you email)
            send_mail(
                subject='Thank You, from The Marina Pizzeria!',
                message=f'Hello {name},\n\nWe received your message: "{message}". Our team will be in touch shortly!\n\nBest,\nThe Marina Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=True,
            )

            # EMAIL B: To Admin to notify
            send_mail(
                subject=f'NEW CONTACT FORM: {name}',
                message=f'New inquiry received from {name} ({user_email}):\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['themarinapizzeria@gmail.com'],
                fail_silently=True,
            )
            messages.success(request, 'The Marina Pizzeria team have received your email and will get in touch soon.')
            return redirect('contact')

    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
                'email': request.user.email
            }
        form = ContactForm(initial=initial_data)

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
            d = {'username': username}
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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f' Hello, {user.username}!')
            return redirect('login_redirect')
    else:
        form = AuthenticationForm()
    return render(request, 'bookings/login.html', {'form': form, 'title': 'log in'})


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


@staff_member_required
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


@staff_member_required(login_url='login')
def staff_register_customer(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('index')

    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        # 1. We include the BookingForm here to catch the date/time errors
        booking_form = BookingForm(request.POST) 

        if user_form.is_valid() and booking_form.is_valid():
            # Create the User
            new_user = user_form.save()
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            new_user.groups.add(customer_group)

            # 2. Get the cleaned data from the booking form
            b_date = booking_form.cleaned_data['booking_date']
            b_time = booking_form.cleaned_data['booking_time']
            p_num = int(booking_form.cleaned_data['party_number'])

            # 3. Table search logic (same as your other views)
            requested_dt = datetime.combine(b_date, b_time)
            suitable_tables = Table.objects.filter(seating_capacity__gte=p_num).order_by('seating_capacity')
            
            assigned_table = None
            buffer = timedelta(hours=1, minutes=59)
            start_buf, end_buf = (requested_dt - buffer).time(), (requested_dt + buffer).time()

            for table in suitable_tables:
                if not Booking.objects.filter(table_id=table, booking_date=b_date, booking_time__range=(start_buf, end_buf)).exists():
                    assigned_table = table
                    break

            if assigned_table:
                Booking.objects.create(
                    User_id=new_user,
                    party_number=p_num,
                    booking_date=b_date,
                    booking_time=b_time,
                    table_id=assigned_table,
                    status=1
                )
                messages.success(request, f"Account & Table reserved for {new_user.username}!")
            else:
                messages.warning(request, f"Account created for {new_user.username}, but no tables were available.")
            
            return redirect('staff_dashboard')
    else:
        user_form = UserCreationForm()
        booking_form = BookingForm()

    return render(request, 'bookings/staff_register.html', {
        'form': user_form, 
        'booking_form': booking_form
    })


# function for staff portal where they can choose to view reservations of all guests, make reservations, register guests at the marina pizzeria
@staff_member_required
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


# function for staff to be able to updatemake a guest booking
@staff_member_required
def staff_manual_booking(request):
    if not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('index')

    if request.method == 'POST':
        form = StaffBookingForm(request.POST)
        if form.is_valid():
            # This 'booking_time' is now a proper time object thanks to our new clean() method
            booking_date = form.cleaned_data['booking_date']
            booking_time = form.cleaned_data['booking_time']
            party_number = int(form.cleaned_data['party_number'])
            selected_customer = form.cleaned_data['customer']
            requested_datetime = datetime.combine(booking_date, booking_time)
            buffer = timedelta(hours=1, minutes=59)
            start_buffer = (requested_datetime - buffer).time()
            end_buffer = (requested_datetime + buffer).time()

            suitable_tables = Table.objects.filter(seating_capacity__gte=party_number).order_by('seating_capacity')

            assigned_table = None
            for table in suitable_tables:
                is_occupied = Booking.objects.filter(
                    table_id=table,
                    booking_date=booking_date,
                    booking_time__range=(start_buffer, end_buffer)
                ).exists()

                if not is_occupied:
                    assigned_table = table
                    break

            if assigned_table:
                booking = form.save(commit=False)
                booking.User_id = selected_customer
                booking.table_id = assigned_table
                booking.status = 1
                booking.save()
                messages.success(request, f"Confirmed! Booking created for {selected_customer.username}.")
                return redirect('staff_dashboard')
            else:
                messages.error(request, "Conflict: No tables available for this time slot.")
    else:
        form = StaffBookingForm()

    return render(request, 'bookings/staff_manual_booking.html', {'form': form})


# function for staff to be able to cancel guest bookings
@staff_member_required
def staff_cancel_booking(request, booking_id):
    # Only allow staff members to delete
    if not request.user.is_staff and not request.user.groups.filter(name='Staff').exists():
        messages.error(request, "Access denied.")
        return redirect('index')

    booking = get_object_or_404(Booking, booking_id=booking_id)

    if request.method == "POST":
        booking.delete()
        messages.success(request, "The reservation has been deleted.")

    return redirect('staff_dashboard')


# function for staff to be able to update guest bookings
@staff_member_required
def staff_update_booking(request, booking_id):
    # 1. FETCH: Get the booking (Staff can edit ANY booking, not just their own)
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if request.method == "POST":
        form = UpdateBookingForm(request.POST, instance=booking)
        
        if form.is_valid():
            new_date = form.cleaned_data['booking_date']
            
            # --- CHECK A: THE TIME MACHINE ---
            if new_date < timezone.now().date():
                messages.error(request, "Error: You cannot move a booking into the past.")
                # Stay on the page so they can fix it
                return render(request, 'bookings/bookings.html', {'form_booking': form, 'booking': booking})

            # --- CHECK B: TIME CONVERSION ---
            time_data = form.cleaned_data['booking_time'] 
            if isinstance(time_data, str):
                new_time = datetime.strptime(time_data, '%H:%M').time()
            else:
                new_time = time_data

            # --- CHECK C: TABLE AVAILABILITY (The "Engine") ---
            new_party = int(form.cleaned_data['party_number'])
            requested_dt = datetime.combine(new_date, new_time)
            buffer = timedelta(hours=1, minutes=59)
            start_buffer = (requested_dt - buffer).time()
            end_buffer = (requested_dt + buffer).time()
            
            # Find suitable tables
            suitable_tables = Table.objects.filter(seating_capacity__gte=new_party).order_by('seating_capacity')

            assigned_table = None
            for table in suitable_tables:
                # IMPORTANT: .exclude(booking_id=booking_id) so the booking doesn't block itself
                is_occupied = Booking.objects.filter(
                    table_id=table,
                    booking_date=new_date,
                    booking_time__range=(start_buffer, end_buffer)
                ).exclude(booking_id=booking_id).exists()

                if not is_occupied:
                    assigned_table = table
                    break

            # 2. SAVE: If a table was found, commit changes
            if assigned_table:
                updated_booking = form.save(commit=False)
                updated_booking.booking_time = new_time 
                updated_booking.table_id = assigned_table
                updated_booking.save()
                messages.success(request, f"Booking for {booking.User_id.username} updated successfully!")
                return redirect('staff_dashboard')
            else:
                messages.error(request, f"No tables available for {new_party} guests at {new_time.strftime('%H:%M')}.")
        else:
            messages.error(request, "Invalid data. Please check the form fields.")
            
    else:
        # 3. GET: Pre-fill the form (the dropdowns will handle the rest)
        form = UpdateBookingForm(instance=booking)
    
    # Render the same "Smart" template from yesterday
    return render(request, 'bookings/bookings.html', {
        'form_booking': form, 
        'booking': booking
    })