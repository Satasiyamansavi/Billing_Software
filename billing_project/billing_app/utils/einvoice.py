import json
from datetime import datetime

def generate_einvoice_json(invoice, items):
    data = {
        "Version": "1.1",
        "TranDtls": {
            "TaxSch": "GST",
            "SupTyp": "B2B"
        },
        "DocDtls": {
            "Typ": "INV",
            "No": str(invoice.id),
            "Dt": invoice.date.strftime("%d/%m/%Y")
        },
        "SellerDtls": {
            "Gstin": "22AAAAA0000A1Z5",
            "LglNm": "Your Company",
        },
        "BuyerDtls": {
            "LglNm": invoice.customer.name,
            "State": invoice.customer.state
        },
        "ItemList": [],
        "ValDtls": {
            "TotInvVal": float(invoice.total)
        }
    }

    for i, item in enumerate(items, start=1):
        data["ItemList"].append({
            "SlNo": str(i),
            "PrdDesc": item.product.name,
            "Qty": item.quantity,
            "UnitPrice": item.product.price,
            "TotAmt": item.subtotal
        })

    return data


# 🔥 FAKE IRN (Demo)
def generate_irn(invoice_id):
    return f"IRN{invoice_id}{datetime.now().timestamp()}"