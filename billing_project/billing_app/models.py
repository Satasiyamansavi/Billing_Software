from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string



# USER ROLE
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Dealer', 'Dealer'),
        ('Staff', 'Staff'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username                   

# BRAND
class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# PRODUCT (Inventory Control)
class Product(models.Model):
    name = models.CharField(max_length=100)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    price = models.FloatField()
    stock = models.IntegerField(default=0)
    low_stock_limit = models.IntegerField(default=5)
    hsn = models.CharField(max_length=20, blank=True, null=True)
    gst = models.FloatField(default=18)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    parent = models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name='children')
    def __str__(self):
        return self.name
    
class Variant(models.Model):
    COLUMN_CHOICES = [
        ("MAIN", "Main"),
        ("2P", "2P"),
        ("AUXA", "Aux-A"),
        ("AUXB", "Aux-B"),
        ("3", "3"),
        ("4", "4"),
        ("5", "5"),
        ("6", "6"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=50, blank=True, null=True)
    column = models.CharField(max_length=10,choices=COLUMN_CHOICES,null=True,blank=True)
    price = models.FloatField()

    def __str__(self):
        return f"{self.product.name} - {self.column}"

class Branch(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class BranchStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.branch.name}"
# CUSTOMER
class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    state = models.CharField(max_length=50, default="Gujarat")
    gstin = models.CharField(max_length=20, blank=True, null=True)
    discount = models.FloatField(default=0)   
    pan = models.CharField(max_length=10, blank=True, null=True)   
    def __str__(self):
        return self.name

    def generate_pan(self):
        letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        numbers = ''.join(random.choices(string.digits, k=4))
        last = random.choice(string.ascii_uppercase)
        return letters + numbers + last

    def generate_gstin(self):
        state_code = "24"  # Gujarat

        if not self.pan:
            self.pan = self.generate_pan()

        entity = "1"
        return f"{state_code}{self.pan}{entity}Z5"

    def save(self, *args, **kwargs):

        if not self.pan:
           self.pan = self.generate_pan()

        if not self.gstin:
           self.gstin = self.generate_gstin()

        super().save(*args, **kwargs)

# SUPPLIER
class Supplier(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# INVOICE (GST)
class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    cgst = models.FloatField(default=0)
    sgst = models.FloatField(default=0)
    igst = models.FloatField(default=0)
    amount_words = models.TextField(blank=True)

    def __str__(self):
        return f"Invoice {self.id}"


# INVOICE ITEM
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    subtotal = models.FloatField()
    price = models.FloatField(null=True, blank=True)
    hsn = models.CharField(max_length=20, blank=True, null=True)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, null=True, blank=True)


# PAYMENT
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50)
    note = models.CharField(max_length=200, blank=True)
    date = models.DateTimeField(auto_now_add=True)


# PURCHASE
class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)  # 👈 ADD THIS
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True)

    quantity = models.IntegerField()
    price = models.FloatField()
    total = models.FloatField()

    date = models.DateTimeField(auto_now_add=True)

# SALES RETURN
class SalesReturn(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField()

    def __str__(self):
        return self.product.name


# PURCHASE RETURN
class PurchaseReturn(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField()

    def __str__(self):
        return self.product.name
    
# 🚗 Vehicle Model
class VehicleModel(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# 🔗 Product ↔ Vehicle Mapping
class ProductVehicle(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(VehicleModel, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.product} - {self.vehicle}"


# 🔁 Alternate Parts
class AlternatePart(models.Model):
    main_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='main')
    alternate_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alternate')

    def __str__(self):
        return f"{self.main_product} → {self.alternate_product}"
    
class StockTransfer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='from_branch')
    to_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='to_branch')
    quantity = models.IntegerField()
    date = models.DateTimeField(default=timezone.now)

# DEALER
class Dealer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dealer'   # ✅ VERY IMPORTANT
    )
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username


# DEALER ORDER
class DealerOrder(models.Model):
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.dealer}"


# DEALER ORDER ITEM
class DealerOrderItem(models.Model):
    order = models.ForeignKey(DealerOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.IntegerField()

    def __str__(self):
        return self.product.name
    
# 👨‍💼 Salesman
class Salesman(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username


# 👥 Customer assign to Salesman
class CustomerAssign(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    salesman = models.ForeignKey(Salesman, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('customer', 'salesman')  # جلوگیری duplicate

    def __str__(self):
        return f"{self.customer.name} → {self.salesman.user.username}"


# 📍 Visit Tracking
class Visit(models.Model):
    salesman = models.ForeignKey(Salesman, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.salesman} visited {self.customer}"