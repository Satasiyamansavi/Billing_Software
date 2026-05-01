from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required , user_passes_test
from django.db.models import Sum, F , Q
from django.db.models.functions import TruncDate , TruncMonth, TruncDay, TruncYear, TruncWeek
from django.http import HttpResponse
from io import BytesIO
from .utils.common import amount_in_words
from .models import Invoice, InvoiceItem , Purchase , Dealer, DealerOrder, DealerOrderItem, Product ,UserProfile , Customer , Variant , BranchStock ,Category
from decimal import Decimal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from .utils.einvoice import generate_einvoice_json, generate_irn
from .utils.ewaybill import generate_ewaybill_data
import json
from .models import *
from .forms import *
import urllib.parse
from .forms import ProductForm

def is_admin(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'Admin'

def is_dealer(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'Dealer'

def is_staff(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'Staff'

def is_dealer_or_admin(user):
    return hasattr(user, 'userprofile') and user.userprofile.role in ['Dealer', 'Admin']

# 🔐 LOGIN
def login_view(request):
    if request.method == "POST":
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user:
            login(request, user)

            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'Staff'}  
            )

            if user.username.lower() == "dealer":
                profile.role = "Dealer"
                profile.save()

                Dealer.objects.get_or_create(
                    user=user,
                    defaults={'phone': '0000000000'}
                )

            role = profile.role

            if role == 'Admin':
                return redirect('dashboard')

            elif role == 'Dealer':
                return redirect('dealer_dashboard')

            else:
                return redirect('dashboard')

        else:
            return HttpResponse("Invalid Username or Password")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')

def dashboard(request):

    filter_type = request.GET.get('filter', 'monthly')

    customer_count = Customer.objects.count()
    product_count = Product.objects.count()
    invoice_count = Invoice.objects.count()

    total_sales = Invoice.objects.aggregate(total=Sum('total'))['total'] or 0
    total_purchase = Purchase.objects.aggregate(total=Sum('total'))['total'] or 0

    total_sales = Decimal(str(total_sales))
    total_purchase = Decimal(str(total_purchase))

    profit_total = total_sales - total_purchase

    if filter_type == "daily":
        sales_qs = Invoice.objects.annotate(d=TruncDay('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncDay('date'))
        fmt = "%d %b"

    elif filter_type == "weekly":
        sales_qs = Invoice.objects.annotate(d=TruncWeek('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncWeek('date'))
        fmt = "Week %W"

    elif filter_type == "yearly":
        sales_qs = Invoice.objects.annotate(d=TruncYear('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncYear('date'))
        fmt = "%Y"

    else:
        sales_qs = Invoice.objects.annotate(d=TruncMonth('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncMonth('date'))
        fmt = "%b %Y"

    sales_data = sales_qs.values('d').annotate(total=Sum('total')).order_by('d')
    purchase_data = purchase_qs.values('d').annotate(total=Sum('total')).order_by('d')

    purchase_map = {
        item['d']: Decimal(str(item['total'] or 0))
        for item in purchase_data
    }

    table_data = []
    labels, sales, purchase, profit = [], [], [], []

    for item in sales_data:
        date = item['d']

        s = Decimal(str(item['total'] or 0))
        p = purchase_map.get(date, Decimal('0'))
        pr = s - p

        label = date.strftime(fmt)

        table_data.append({
            "period": label,
            "sales": float(s),
            "purchase": float(p),
            "profit": float(pr),
        })

        labels.append(label)
        sales.append(float(s))
        purchase.append(float(p))
        profit.append(float(pr))

    return render(request, 'dashboard.html', {
        'customer_count': customer_count,
        'product_count': product_count,
        'invoice_count': invoice_count,

        'total_sales': float(total_sales),
        'total_purchase': float(total_purchase),
        'profit_total': float(profit_total),

        'table_data': table_data,

        'months': json.dumps(labels),
        'sales': json.dumps(sales),
        'purchase': json.dumps(purchase),
        'profit': json.dumps(profit),

        'selected_filter': filter_type
    })

# 👤 CUSTOMER
def customer_list(request):
    data = Customer.objects.all()
    edit_id = request.GET.get('edit')

    customer = Customer.objects.get(id=edit_id) if edit_id else None

    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')

        if customer:  
            customer.name = name
            customer.phone = phone
            customer.address = address
            customer.save()
        else:  
            Customer.objects.create(
                name=name,
                phone=phone,
                address=address
            )

        return redirect('customer')

    return render(request, 'customer.html', {
        'data': data,
        'customer_to_edit': customer
    })

    if form.is_valid():
        form.save()
        return redirect('customer')

    return render(request, 'customer.html', {
        'data': data,
        'form': form
    })


def delete_customer(request, id):
    Customer.objects.filter(id=id).delete()
    return redirect('customer')


# 📦 PRODUCT + 🔍 SEARCH
def product_list(request):
    query = request.GET.get('q')

    # 🔍 SEARCH
    if query:
        all_products = Product.objects.filter(name__icontains=query)
    else:
        all_products = Product.objects.all()

    branches = Branch.objects.all()

    # 🔥 COLUMN STRUCTURE
    columns = ['MAIN', '2P', 'AUXA', 'AUXB', '3', '4', '5', '6']

    # 🔥 MAIN PRODUCTS ONLY
    main_products = all_products.filter(parent__isnull=True)

    final_data = []

    for p in main_products:

        # 🔹 VARIANTS
        p.variant_list = p.variants.all()

        # 🔹 BRANCH STOCK
        p.branch_stock = {}
        for b in branches:
            stock = BranchStock.objects.filter(product=p, branch=b).aggregate(
                total=Sum('stock')
            )['total'] or 0

            p.branch_stock[b.id] = stock

        p.total_stock = sum(p.branch_stock.values())

        # 🔥 SUB PRODUCTS
        subs = Product.objects.filter(parent=p)

        for s in subs:
            s.variant_list = s.variants.all()

            s.branch_stock = {}
            for b in branches:
                stock = BranchStock.objects.filter(product=s, branch=b).aggregate(
                    total=Sum('stock')
                )['total'] or 0

                s.branch_stock[b.id] = stock

            s.total_stock = sum(s.branch_stock.values())

        final_data.append({
            "product": p,
            "subs": subs
        })

    # 🔥 EDIT MODE
    edit_id = request.GET.get('edit')
    product = Product.objects.filter(id=edit_id).first()

    form = ProductForm(request.POST or None, instance=product)

    # 🔥 SAVE PRODUCT + VARIANTS
    if request.method == "POST" and form.is_valid():
        product = form.save()

        sizes = request.POST.getlist('size[]')
        prices = request.POST.getlist('price[]')

        # OLD DELETE
        product.variants.all().delete()

        # SAVE NEW
        for i, (s, p_val) in enumerate(zip(sizes, prices)):
            if s and p_val:
                Variant.objects.create(
                    product=product,
                    size=s,
                    price=p_val,
                    column=s if i < len(columns) else 'MAIN'
                )

        return redirect('product')

    return render(request, 'product.html', {
        'data': final_data,
        'form': form,
        'product_to_edit': product,
        'columns': columns,
        'branches': branches
    })


def delete_product(request, id):
    Product.objects.filter(id=id).delete()
    return redirect('product')
    
# 🧾 INVOICE (GST UPDATED)

def create_invoice(request):
    customers = Customer.objects.all()
    branches = Branch.objects.all()
    products = Product.objects.all()

    # 🔥 PRODUCT JSON (MISSING BEFORE)
    product_data = {
        str(p.id): {
            "name": p.name,
        } for p in products
    }

    # 🔥 VARIANT DATA
    variant_data = {}
    for v in Variant.objects.select_related('product'):
        variant_data.setdefault(str(v.product_id), [])
        variant_data[str(v.product_id)].append({
            "id": str(v.id),
            "size": v.size,
            "price": float(v.price)
        })

    # 🔥 STOCK DATA (variant-wise)
    stock_data = {}
    for bs in BranchStock.objects.select_related('product', 'branch'):
        for v in bs.product.variants.all():
            stock_data.setdefault(str(bs.branch_id), {})
            stock_data[str(bs.branch_id)][str(v.id)] = bs.stock

    # 🔥 CUSTOMER DATA
    customer_data = {
        str(c.id): {
            "name": c.name,
            "discount": float(getattr(c, 'discount', 0)),
            "state": c.state or '',
            "phone": getattr(c, 'phone', '') or '',
            "address": c.address or '',
        } for c in customers
    }

    if request.method == "POST":
        customer = Customer.objects.get(id=request.POST.get('customer'))
        branch = Branch.objects.get(id=request.POST.get('branch'))

        variant_ids = request.POST.getlist('variant[]')
        qtys = request.POST.getlist('qty[]')

        discount = float(request.POST.get('cust_discount', 0))

        subtotal = 0
        items_data = []

        for v_id, q in zip(variant_ids, qtys):
            if not v_id or not q:
                continue

            variant = Variant.objects.get(id=v_id)
            product = variant.product
            qty = int(q)

            branch_stock = BranchStock.objects.get(product=product, branch=branch)

            if branch_stock.stock < qty:
                return render(request, 'invoice.html', {
                    'error': f"Not enough stock for {product.name} ({variant.size})",
                    'customers': customers,
                    'products': products,
                    'branches': branches,
                    'customer_json': json.dumps(customer_data),
                    'product_json': json.dumps(product_data),
                    'variant_json': json.dumps(variant_data),
                    'stock_json': json.dumps(stock_data),
                })

            price = float(variant.price)
            discounted_price = price - (price * discount / 100)

            base_total = discounted_price * qty
            gst = product.gst or 18
            gst_amount = base_total * gst / 100
            item_total = base_total + gst_amount

            subtotal += item_total

            items_data.append((product, variant, qty, discounted_price, item_total))

        invoice = Invoice.objects.create(
            customer=customer,
            branch=branch,
            subtotal=round(subtotal, 2),
            cgst=0,
            sgst=0,
            igst=0,
            total=round(subtotal),
            amount_words=amount_in_words(round(subtotal))
        )

        for product, variant, qty, price, item_total in items_data:
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                variant=variant,
                quantity=qty,
                price=round(price, 2),
                subtotal=round(item_total, 2),
                hsn=product.hsn
            )

            bs = BranchStock.objects.get(product=product, branch=branch)
            bs.stock = F('stock') - qty
            bs.save()

        return redirect('invoice_view', invoice.id)

    return render(request, 'invoice.html', {
        'customers': customers,
        'products': products,
        'branches': branches,
        'customer_json': json.dumps(customer_data),
        'product_json': json.dumps(product_data),
        'variant_json': json.dumps(variant_data),
        'stock_json': json.dumps(stock_data),
    })

# 👁️ VIEW INVOICE
from collections import defaultdict

def view_invoice(request, id):
    invoice = Invoice.objects.get(id=id)
    items = InvoiceItem.objects.filter(invoice=invoice).select_related('product')

    hsn_summary = defaultdict(lambda: {'taxable':0, 'cgst':0, 'sgst':0})

    for item in items:
        hsn = item.hsn or "N/A"

        gst = item.product.gst or 18

        total_with_gst = item.subtotal

        taxable = total_with_gst / (1 + gst/100)

        gst_amount = total_with_gst - taxable

        cgst = gst_amount / 2
        sgst = gst_amount / 2

        hsn_summary[hsn]['taxable'] += taxable
        hsn_summary[hsn]['cgst'] += cgst
        hsn_summary[hsn]['sgst'] += sgst

    hsn_data = [
        {
            'hsn': hsn,
            'taxable': round(val['taxable'], 2),
            'cgst': round(val['cgst'], 2),
            'sgst': round(val['sgst'], 2),
            'total_tax': round(val['cgst'] + val['sgst'], 2)
        }
        for hsn, val in hsn_summary.items()
    ]

    return render(request, 'invoice_view.html', {
        'invoice': invoice,
        'items': items,
        'hsn_data': hsn_data
    })

# 📄 INVOICE LIST
def invoice_list(request):
    invoices = Invoice.objects.all().order_by('-date')

    invoice_data = []

    for inv in invoices:
        paid = Payment.objects.filter(invoice=inv).aggregate(Sum('amount'))['amount__sum'] or 0
        due = inv.total - paid

        invoice_data.append({
            'invoice': inv,
            'paid': paid,
            'due': due
        })

    return render(request, 'invoice_list.html', {
        'invoice_data': invoice_data
    })

def delete_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)

    if request.method == "POST":
        invoice.delete()

    return redirect('invoice_list')

# 💳 PAYMENT
def payment(request):
    if request.method == "POST":
        amount = Decimal(request.POST.get('amount'))

        Payment.objects.create(
            customer_id=request.POST.get('customer'),
            invoice_id=request.POST.get('invoice') or None,
            amount=amount,
            method=request.POST.get('method'),
            note=request.POST.get('note')
        )

        return redirect('payment')

    data = Payment.objects.values(
        'invoice_id',
        'invoice__id',
        'customer__name'
    ).annotate(
        total_amount=Sum('amount')
    ).order_by('-invoice_id')

    return render(request, 'payment.html', {
        'data': data,
        'customers': Customer.objects.all(),
        'invoices': Invoice.objects.all()
    })

# 🛒 PURCHASE

def purchase_list(request):
    data = Purchase.objects.all()
    form = PurchaseForm(request.POST or None)
    branches = Branch.objects.all()

    if request.method == "POST" and form.is_valid():
        purchase = form.save(commit=False)

        purchase.total = purchase.quantity * purchase.price

        product = purchase.product
        branch = purchase.branch
        qty = purchase.quantity

        stock, created = BranchStock.objects.get_or_create(
            product=product,
            branch=branch,
            defaults={'stock': 0}
        )

        stock.stock += qty
        stock.save()

        purchase.save()

        return redirect('purchase')

    return render(request, 'purchase.html', {
        'data': data,
        'form': form,
        'branches': branches
    })

# ⚠️ LOW STOCK (UPDATED)

def low_stock(request):
    products = Product.objects.all()

    items = []

    for p in products:
        total_stock = BranchStock.objects.filter(product=p).aggregate(
            total=Sum('stock')
        )['total'] or 0

        if total_stock <= (p.low_stock_limit or 0):
            p.stock = total_stock
            items.append(p)

    return render(request, 'low_stock.html', {'items': items})

from django.utils import timezone
from datetime import timedelta

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def profit_report(request):

    filter_type = request.GET.get('filter', 'monthly')

    total_sales = Invoice.objects.aggregate(total=Sum('total'))['total'] or 0
    total_purchase = Purchase.objects.aggregate(total=Sum('total'))['total'] or 0

    total_sales = Decimal(str(total_sales))
    total_purchase = Decimal(str(total_purchase))
    total_profit = total_sales - total_purchase

    if filter_type == "daily":
        sales_qs = Invoice.objects.annotate(d=TruncDay('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncDay('date'))
        fmt = "%d %b"

    elif filter_type == "weekly":
        sales_qs = Invoice.objects.annotate(d=TruncWeek('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncWeek('date'))
        fmt = "Week %W"

    elif filter_type == "yearly":
        sales_qs = Invoice.objects.annotate(d=TruncYear('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncYear('date'))
        fmt = "%Y"

    else:
        sales_qs = Invoice.objects.annotate(d=TruncMonth('date'))
        purchase_qs = Purchase.objects.annotate(d=TruncMonth('date'))
        fmt = "%b %Y"

    sales_data = sales_qs.values('d').annotate(total=Sum('total')).order_by('d')
    purchase_data = purchase_qs.values('d').annotate(total=Sum('total')).order_by('d')

    purchase_map = {i['d']: Decimal(str(i['total'] or 0)) for i in purchase_data}

    table_data = []

    for i in sales_data:
        date = i['d']

        s = Decimal(str(i['total'] or 0))
        p = purchase_map.get(date, Decimal('0'))
        pr = s - p

        table_data.append({
            "period": date.strftime(fmt),
            "sales": float(s),
            "purchase": float(p),
            "profit": float(pr),
        })

    return render(request, "profit.html", {
        "total_sales": float(total_sales),
        "total_purchase": float(total_purchase),
        "total_profit": float(total_profit),

        "table_data": table_data,
        "selected_filter": filter_type

    })

# 📊 SALES CHART
def sales_chart(request):
    data = Invoice.objects.annotate(
        date_only=TruncDate('date')
    ).values('date_only').annotate(total=Sum('total'))

    return render(request, 'sales_chart.html', {
        'labels': [str(d['date_only']) for d in data],
        'totals': [float(d['total']) for d in data]
    })

# 📊 OUTSTANDING REPORT (NEW)
@user_passes_test(is_admin)
def outstanding_report(request):
    customers = Customer.objects.all()
    data = []

    for c in customers:
        total = Invoice.objects.filter(customer=c).aggregate(Sum('total'))['total__sum'] or 0
        paid = Payment.objects.filter(customer=c).aggregate(Sum('amount'))['amount__sum'] or 0

        total = float(total)
        paid = float(paid)

        data.append({
            'customer': c,
            'total': total,
            'paid': paid,
            'outstanding': total - paid
        })

    return render(request, 'outstanding.html', {'data': data})

# 📊 ITEM SALES REPORT (NEW)
@user_passes_test(is_admin)
def item_sales_report(request):
    data = InvoiceItem.objects.values('product__name').annotate(
        total_qty=Sum('quantity')
    )
    return render(request, 'item_sales.html', {'data': data})

# 🧾 PDF
import pdfkit
from django.template.loader import render_to_string

def generate_invoice_pdf(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    items = InvoiceItem.objects.filter(invoice=invoice).select_related('product')

    html = render_to_string('invoice_view.html', {
        'invoice': invoice,
        'items': items,
        'pdf': True
    })

    config = pdfkit.configuration(
        wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    )

    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'

    return response

def sales_return(request):
    invoices = Invoice.objects.all()
    products = Product.objects.all()

    if request.method == "POST":
        invoice = Invoice.objects.get(id=request.POST['invoice'])
        product = Product.objects.get(id=request.POST['product'])
        qty = int(request.POST['qty'])

        SalesReturn.objects.create(
            invoice=invoice,
            product=product,
            qty=qty
        )

        product.stock += qty
        product.save()

        return redirect('sales_return')

    return render(request, 'sales_return.html', {
        'invoices': invoices,
        'products': products,
        'data': SalesReturn.objects.all()
    })

def purchase_return(request):
    purchases = Purchase.objects.all()
    products = Product.objects.all()

    if request.method == "POST":
        purchase = Purchase.objects.get(id=request.POST['purchase'])
        product = Product.objects.get(id=request.POST['product'])
        qty = int(request.POST['qty'])

        PurchaseReturn.objects.create(
            purchase=purchase,
            product=product,
            qty=qty
        )

        BranchStock.stock -= qty
        product.save()

        return redirect('purchase_return')

    return render(request, 'purchase_return.html', {
        'purchases': purchases,
        'products': products,
        'data': PurchaseReturn.objects.all()
    })

def supplier_report(request):
    suppliers = Supplier.objects.all()
    data = []

    for s in suppliers:
        total = Purchase.objects.filter(supplier=s).aggregate(Sum('total'))['total__sum'] or 0

        data.append({
            'supplier': s,
            'total': total
        })

    return render(request, 'supplier_report.html', {'data': data})

@user_passes_test(is_admin)
def cashbook(request):
    payments = Payment.objects.all().order_by('-date')

    total_in = Payment.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'cashbook.html', {
        'payments': payments,
        'total': total_in
    })

def vehicle_mapping(request):
    vehicles = VehicleModel.objects.all()
    products = Product.objects.all()

    if request.method == "POST":
        ProductVehicle.objects.create(
            product_id=request.POST['product'],
            vehicle_id=request.POST['vehicle']
        )
        return redirect('vehicle_mapping')

    return render(request, 'vehicle_mapping.html', {
        'vehicles': vehicles,
        'products': products,
        'data': ProductVehicle.objects.all()
    })

def vehicle_mapping_edit(request, id):
    obj = ProductVehicle.objects.get(id=id)   

    if request.method == "POST":
        obj.product_id = request.POST['product']
        obj.vehicle_id = request.POST['vehicle']
        obj.save()
        return redirect('vehicle_mapping')

    return render(request, 'vehicle_mapping_edit.html', {
        'obj': obj,
        'products': Product.objects.all(),
        'vehicles': VehicleModel.objects.all()
    })

def vehicle_mapping_delete(request, id):
    obj = ProductVehicle.objects.get(id=id)   
    obj.delete()
    return redirect('vehicle_mapping')

def barcode_billing(request):
    product = None

    if request.method == "POST":
        code = request.POST['barcode']
        product = Product.objects.filter(barcode=code).first()

    return render(request, 'barcode.html', {'product': product})

def fast_moving(request):
    data = InvoiceItem.objects.values('product__name').annotate(
        total=Sum('quantity')
    ).order_by('-total')[:10]

    return render(request, 'fast_moving.html', {'data': data})

def dead_stock(request):
    data = Product.objects.filter(stock__gt=0).exclude(
        invoiceitem__isnull=False
    )

    return render(request, 'dead_stock.html', {'data': data})

def owner_dashboard(request):
    return render(request, 'owner_dashboard.html', {
        'sales': Invoice.objects.aggregate(Sum('total'))['total__sum'] or 0,
        'stock': Product.objects.aggregate(Sum('stock'))['stock__sum'] or 0,
        'customers': Customer.objects.count()
    })

def branch_view(request):
    if request.method == "POST":
        Branch.objects.create(name=request.POST['name'])
        return redirect('branch')

    return render(request, 'branch.html', {
        'data': Branch.objects.all()
    })

def branch_edit(request, id):
    branch = Branch.objects.get(id=id)

    if request.method == "POST":
        branch.name = request.POST['name']
        branch.save()
        return redirect('branch')

    return render(request, 'branch_edit.html', {'branch': branch})

def branch_delete(request, id):
    branch = Branch.objects.get(id=id)
    branch.delete()
    return redirect('branch')

def stock_transfer(request):
    products = Product.objects.all()
    branches = Branch.objects.all()
    branch_stock = BranchStock.objects.all()

    if request.method == "POST":
        product = Product.objects.get(id=request.POST['product'])
        from_branch = Branch.objects.get(id=request.POST['from_branch'])
        to_branch = Branch.objects.get(id=request.POST['to_branch'])
        qty = int(request.POST['qty'])

        from_stock = BranchStock.objects.filter(
            product=product,
            branch=from_branch
        ).first()

        if not from_stock:
            return HttpResponse("No stock available in FROM branch")

        if from_stock.stock < qty:
            return HttpResponse("Not enough stock in FROM branch")

        from_stock.stock -= qty
        from_stock.save()

        to_stock, created = BranchStock.objects.get_or_create(
            product=product,
            branch=to_branch,
            defaults={'stock': 0}
        )

        to_stock.stock += qty
        to_stock.save()

        StockTransfer.objects.create(
            product=product,
            from_branch=from_branch,
            to_branch=to_branch,
            quantity=qty
        )

        total_stock = BranchStock.objects.filter(product=product).aggregate(
            total=Sum('stock')
        )['total'] or 0

        product.stock = total_stock
        product.save()

        return redirect('stock_transfer')

    return render(request, 'stock_transfer.html', {
        'products': products,
        'branches': branches,
        'branch_stock': branch_stock
    })

# 🧑‍💼 DEALER DASHBOARD
@user_passes_test(is_dealer_or_admin)
def dealer_dashboard(request):

    if request.user.userprofile.role == 'Dealer':
        dealer = Dealer.objects.filter(user=request.user).first()
        products = Product.objects.filter(stock__gt=0)

    else:  
        products = Product.objects.all()

    return render(request, 'dealer_dashboard.html', {'products': products})

# 🛒 PLACE ORDER
@login_required
def dealer_place_order(request):

    dealer = Dealer.objects.filter(user=request.user).first()

    if not dealer:
        return HttpResponse("Access Denied: Only Dealer can place order")

    if request.method == "POST":

        order = DealerOrder.objects.create(dealer=dealer)
        has_item = False   

        for key, value in request.POST.items():

            if not value or value == "":
                continue

            if key.startswith('qty_'):
                try:
                    qty = int(value)
                except:
                    continue

                if qty <= 0:
                    continue

                product_id = key.split('_')[1]
                product = Product.objects.get(id=product_id)

                if qty > product.stock:
                    return HttpResponse(f"Not enough stock for {product.name}")

                DealerOrderItem.objects.create(
                    order=order,
                    product=product,
                    qty=qty
                )

                has_item = True

        if not has_item:
            order.delete()
            return HttpResponse("Please select at least one product")

        return redirect('dealer_orders')

    return redirect('dealer_dashboard')

# 📄 ORDER HISTORY
@login_required
def dealer_orders(request):
    dealer = Dealer.objects.get(user=request.user)
    orders = DealerOrder.objects.filter(dealer=dealer)

    return render(request, 'dealer_orders.html', {'orders': orders})

@login_required
def delete_dealer_order(request, id):
    order = get_object_or_404(DealerOrder, id=id)

    if order.dealer.user != request.user:
        return HttpResponse("Unauthorized", status=403)

    order.delete()
    return redirect('dealer_orders')

def send_whatsapp_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    items = InvoiceItem.objects.filter(invoice=invoice)

    customer = invoice.customer

    phone = customer.phone
    if not phone.startswith('91'):
        phone = '91' + phone

    message = f"🧾 *Invoice #{invoice.id}*\n\n"
    message += f"Customer: {customer.name}\n"
    message += f"Date: {invoice.date.strftime('%d-%m-%Y')}\n\n"

    message += "*Items:*\n"

    for item in items:
        message += f"- {item.product.name} x {item.quantity} = ₹{item.subtotal}\n"

    message += "\n"
    message += f"CGST: ₹{invoice.cgst}\n"
    message += f"SGST: ₹{invoice.sgst}\n"
    message += f"IGST: ₹{invoice.igst}\n"
    message += f"\n💰 *Total: ₹{invoice.total}*"

    encoded_message = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/{phone}?text={encoded_message}"

    return redirect(whatsapp_url)

# 🧾 E-INVOICE
def generate_einvoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    items = InvoiceItem.objects.filter(invoice=invoice)

    data = generate_einvoice_json(invoice, items)
    irn = generate_irn(invoice.id)

    return render(request, 'einvoice.html', {
        'data': data,
        'irn': irn,
        'invoice': invoice   
    })

# 🚚 E-WAY BILL

def generate_ewaybill(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    
    print("Branch:", invoice.branch)

    data = {
        'invoice_no': invoice.id,
        'from_location': invoice.branch.name if invoice.branch else "Main Warehouse",
        'to': invoice.customer.name,
        'vehicle_no': "GJ00XX0000",
        'distance': "N/A",
        'total': invoice.total
    }

    return render(request, 'ewaybill.html', {
        'data': data,
        'invoice': invoice   
    })

# 👨‍💼 ADD SALESMAN
def salesman_list(request):
    data = Salesman.objects.all()
    users = User.objects.exclude(salesman__isnull=False)  

    if request.method == "POST":
        user_id = request.POST.get('user')
        phone = request.POST.get('phone')

        if user_id and phone:
            user = User.objects.get(id=user_id)

            if not Salesman.objects.filter(user=user).exists():
                Salesman.objects.create(user=user, phone=phone)

        return redirect('salesman')

    return render(request, 'salesman.html', {
        'data': data,
        'users': users
    })

# 👥 ASSIGN CUSTOMER
def assign_customer(request):
    if request.method == "POST":
        customer_id = request.POST.get('customer')
        salesman_id = request.POST.get('salesman')

        if customer_id and salesman_id:
            CustomerAssign.objects.get_or_create(
                customer_id=customer_id,
                salesman_id=salesman_id
            )

        return redirect('assign_customer')

    return render(request, 'assign_customer.html', {
        'customers': Customer.objects.all(),
        'salesmen': Salesman.objects.all(),
        'data': CustomerAssign.objects.select_related('customer', 'salesman')
    })

# 📍 ADD VISIT
def add_visit(request):
    if request.method == "POST":
        salesman_id = request.POST.get('salesman')
        customer_id = request.POST.get('customer')
        notes = request.POST.get('notes')

        if salesman_id and customer_id:
            Visit.objects.create(
                salesman_id=salesman_id,
                customer_id=customer_id,
                notes=notes
            )

        return redirect('visit')

    return render(request, 'visit.html', {
        'salesmen': Salesman.objects.all(),
        'customers': Customer.objects.all(),
        'data': Visit.objects.select_related('salesman', 'customer').order_by('-date')
    })

# 📊 REPORT
def salesman_report(request):
    data = Visit.objects.values(
        'salesman__user__username'
    ).annotate(total=models.Count('id'))

    return render(request, 'salesman_report.html', {'data': data})

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

def get_predictions():
    items = InvoiceItem.objects.select_related('invoice', 'product')

    data = []

    for item in items:
        if item.invoice and item.invoice.date:
            data.append({
                'month': item.invoice.date.month,
                'year': item.invoice.date.year,
                'sales': item.quantity,
                'product': item.product.id
            })

    df = pd.DataFrame(data)

    if df.empty:
        return [], []

    predictions = []
    alerts = []

    for product_id in df['product'].unique():
        product_df = df[df['product'] == product_id]

        grouped = (
            product_df
            .groupby(['year', 'month'])['sales']
            .sum()
            .reset_index()
            .sort_values(['year', 'month'])
        )

        product = Product.objects.get(id=product_id)

        if len(grouped) == 1:
            prediction = int(grouped['sales'].iloc[0])
        else:
            grouped['time'] = range(1, len(grouped) + 1)

            X = grouped[['time']]
            y = grouped['sales']

            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42
            )
            model.fit(X, y)

            next_time = [[grouped['time'].max() + 1]]
            prediction = int(model.predict(next_time)[0])

        required = max(prediction - product.stock, 0)

        predictions.append({
            'name': product.name,
            'stock': product.stock,
            'prediction': prediction,
            'required': required
        })

        if product.stock < prediction:
            alerts.append({
                'name': product.name,
                'required': required
            })

    return predictions, alerts


def demand_prediction(request):
    predictions, alerts = get_predictions()

    labels = []
    actual_data = []
    predicted_data = []

    for p in predictions:
        labels.append(p['name'])
        actual_data.append(p['stock'])
        predicted_data.append(p['prediction'])

    return render(request, 'prediction.html', {
        'predictions': predictions,
        'alerts': alerts,
        'labels': labels,
        'actual_data': actual_data,
        'predicted_data': predicted_data
    })


def ai_dashboard(request):
    predictions, alerts = get_predictions()

    return render(request, 'ai_dashboard.html', {
        'predictions': predictions,
        'alerts': alerts,
        'alert_count': len(alerts)
    })