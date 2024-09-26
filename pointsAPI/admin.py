from django.contrib import admin
from .models import Transaction, Payer

admin.site.register(Transaction)
admin.site.register(Payer)