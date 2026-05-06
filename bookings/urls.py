from django.urls import path, include
from django.conf import settings
from . import views
from django.conf.urls.static import static

urlpatterns = [
         path('', views.index, name ='index'),
         path('bookings/', views.bookings, name='bookings'),
         path('menu/', views.menu, name='menu'),
         path('about/', views.about, name='about'),

]