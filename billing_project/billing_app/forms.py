from django import forms
from .models import Customer, Product, Purchase, Branch
from itertools import groupby

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'

class ProductForm(forms.ModelForm):

    parent = forms.ModelChoiceField(
        queryset=Product.objects.filter(parent__isnull=True),
        required=False,
        empty_label="-- Main Product (No Parent) --",
        widget=forms.Select(attrs={
            'class': 'form-control mb-2'
        })
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control mb-2'
        })
    )

    class Meta:

        model = Product

        fields = [
            'name',
            'section',
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
                'placeholder': 'HSN Code'
            }),

            'gst': forms.NumberInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'GST %'
            }),

            'section': forms.TextInput(attrs={
                'class': 'form-control mb-2',
                'placeholder': 'Section (70x16)'
            }),
        }

    # =========================
    # SAVE METHOD
    # =========================

    def save(self, commit=True):

        obj = super().save(commit=False)

        if not obj.parent:
            obj.parent = None

        if commit:
            obj.save()

        return obj

    # =========================
    # INIT
    # =========================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields['parent'].queryset = Product.objects.filter(
            parent__isnull=True
        )

class GroupedModelChoiceField(forms.ModelChoiceField):

    @property
    def choices(self):
        queryset = self.queryset.select_related('parent').order_by('parent__name', 'name')

        grouped = []

        grouped.append(('', '----- Select Product -----'))

        from itertools import groupby
        for parent, items in groupby(queryset, key=lambda x: x.parent):
            if parent:
                grouped.append(
                    (parent.name, [(obj.id, obj.name) for obj in items])
                )

        return grouped
            
class PurchaseForm(forms.ModelForm):

    product = GroupedModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control mb-2'}),
        empty_label="----- Select Product -----"
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['product'].queryset = Product.objects.filter(parent__isnull=False)


