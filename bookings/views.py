from django.shortcuts import render 
from django.http import HttpResponse

# Create your views here.
def my_bookings(request):
    return HttpResponse("This is the bookings page.")