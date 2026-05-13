def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.fields['product'].queryset = Product.objects.filter(parent__isnull=False)