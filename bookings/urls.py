from django.urls import path, include
from django.conf import settings
from . import views
from django.conf.urls.static import static

urlpatterns = [
         path('', views.index, name ='index'),
         path('bookings/', views.bookings, name='bookings'),
         path('menu/', views.menu, name='menu'),
         path('about/', views.about, name='about'),
         path('contact/', views.contact, name='contact'),
         path('booked/', views.booked, name='booked'),
         path('my_bookings/', views.my_bookings, name='my_bookings'),
         path('update_booking/<int:booking_id>/', views.update_booking, name='edit_booking'),
         path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),

]