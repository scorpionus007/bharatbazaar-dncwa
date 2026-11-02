"""Who receives personal data, and what they get.

s.11(1)(b) gives the Data Principal the identities of everyone her
data was shared with. That is only answerable if somebody writes the
list down, so it is here in source rather than in a slide deck, and
the privacy page renders it straight from this constant.

Keeping it next to the code is deliberate: a processor added in a
pull request and not added here is a visible omission in review.
"""

STORAGE_REGION = "ap-south-1"

GRIEVANCE_OFFICER = "grievance.officer@bharatbazaar.example.in"

PROCESSORS = [
    {
        "name": "MSG91",
        "purpose": "Sending the one time password and order updates by SMS",
        "data_shared": "Mobile number, your name, order number",
        "region": "India",
        "lawful_basis": "Necessary to provide the service you asked for",
    },
    {
        "name": "Razorpay",
        "purpose": "Taking the payment",
        "data_shared": "Order amount, payment identifier, UPI handle or card last four",
        "region": "India",
        "lawful_basis": "Necessary to complete the transaction",
    },
    {
        "name": "Delhivery",
        "purpose": "Delivering the parcel in metro pincodes",
        "data_shared": "Recipient name, phone number, delivery address",
        "region": "India",
        "lawful_basis": "Necessary to deliver what you ordered",
    },
    {
        "name": "Bluedart",
        "purpose": "Delivering the parcel elsewhere",
        "data_shared": "Recipient name, phone number, delivery address",
        "region": "India",
        "lawful_basis": "Necessary to deliver what you ordered",
    },
]


def recipients_for_display() -> list[dict]:
    return PROCESSORS


def names() -> list[str]:
    return [p["name"] for p in PROCESSORS]
