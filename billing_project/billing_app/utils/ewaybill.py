def generate_ewaybill_data(invoice):
    return {
        "invoice_no": invoice.id,
        "from_location": "Your Warehouse",
        "to": invoice.customer.name,
        "vehicle_no": "GJ01AB1234",
        "distance": "50 km",
        "total": float(invoice.total)
    }