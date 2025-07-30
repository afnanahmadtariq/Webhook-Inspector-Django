from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_webhook, name='create_webhook'),
    path('hooks/<uuid:hook_uuid>/', views.receive_webhook, name='receive_webhook'),
    path('inspect/<uuid:hook_uuid>/', views.inspect_webhook, name='inspect_webhook'),
]
