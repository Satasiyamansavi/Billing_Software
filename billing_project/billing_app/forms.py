from django import forms
from .models import Customer, Product, Purchase, Branch

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

class ProductForm(forms.ModelForm):

    parent = forms.ModelChoiceField(
        queryset=Product.objects.filter(parent__isnull=True),
        required=False,
        empty_label="-- Main Product (No Parent) --",
        widget=forms.Select(attrs={'class': 'form-control mb-2'})
    )

    # 🔥 Branch (Stock માટે use થશે)
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,   # 👈 IMPORTANT (edit સમયે error ના આવે)
        widget=forms.Select(attrs={
            'class': 'form-control mb-2'
        })
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'parent',
            'brand',
            'barcode',
            'price',
            'low_stock_limit',
            'hsn',
            'gst'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Product Name'
            }),
 
            'parent': forms.Select(attrs={
                'class': 'form-control mb-2'
            }),

            'brand': forms.Select(attrs={
                'class': 'form-control mb-2'
            }),

            'barcode': forms.TextInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Barcode'
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Base Price'
            }),

            'low_stock_limit': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Low Stock Limit'
            }),

            'hsn': forms.TextInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'HSN Code (e.g. 9403)'
            }),

            'gst': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'GST % (e.g. 18)'
            }),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        # 👉 always latest parent products
            self.fields['parent'].queryset = Product.objects.filter(parent__isnull=True)
            
class PurchaseForm(forms.ModelForm):

    class Meta:
        model = Purchase
        fields = ['product', 'branch', 'quantity', 'price']

        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control mb-2',
            }),
            'branch': forms.Select(attrs={
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

    # ✅ CORRECT PLACE
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 ONLY SUB PRODUCTS
        self.fields['product'].queryset = Product.objects.filter(parent__isnull=False)
