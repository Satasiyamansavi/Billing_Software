from django import forms
from .models import Customer, Product, Purchase, Branch

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'


class ProductForm(forms.ModelForm):

    # ✅ Branch field (custom)
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control mb-2'})
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'brand',
            'barcode',
            'price',
            'low_stock_limit',
            'hsn',          # ✅ ADD
            'gst'           # ✅ ADD
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'brand': forms.Select(attrs={'class': 'form-control mb-2'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control mb-2'}),
            'price': forms.NumberInput(attrs={'class': 'form-control mb-2'}),
            'low_stock_limit': forms.NumberInput(attrs={'class': 'form-control mb-2'}),

            # ✅ NEW
            'hsn': forms.TextInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Enter HSN Code (e.g. 9403)'
            }),

            'gst': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'GST % (e.g. 18)'
            }),
        }
        
class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['product', 'branch', 'quantity', 'price']   # ✅ branch add

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control mb-2',
            }),
            'branch': forms.Select(attrs={   # ✅ NEW
                'class': 'form-control mb-2',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Quantity'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Price'
            }),
        }

