from django.contrib import admin
from .models import *

admin.site.register(Brand)
admin.site.register(VehicleModel)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'price', 'stock', 'hsn', 'gst')
    search_fields = ('name', 'barcode', 'hsn')
    list_filter = ('brand', 'gst')