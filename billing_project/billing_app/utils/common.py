from num2words import num2words

def amount_in_words(amount):
    amount = round(amount, 2)

    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))

    words = num2words(rupees, lang='en_IN').title() + " Rupees"

    if paise > 0:
        words += " and " + num2words(paise, lang='en_IN').title() + " Paise"

    return words + " Only"