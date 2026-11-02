# BharatBazaar

A marketplace API. Customers sign in with a phone number and an OTP,
browse a catalogue, check out against a saved address, pay through
Razorpay, and track the parcel through Delhivery or Bluedart. Sellers
onboard with a GST number and a KYC pack and are settled weekly.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Layout

```
app/
  config.py            environment and feature settings
  database.py          session wiring
  models/
    customer.py        customers, addresses, saved payment methods, OTP log
    seller.py          sellers, KYC documents, payouts
    catalog.py         categories, products, reviews, browsing events
    order.py           orders, items, payments, delivery tracking
    support.py         tickets, returns, abuse reports
  api/
    auth.py            OTP request and verify, session tokens
    customers.py       profile and addresses
    catalog.py         browse, search, reviews
    cart.py            cart contents
    orders.py          checkout and order history
    payments.py        gateway initiation and webhook
    sellers.py         onboarding, KYC upload, dashboard
    support.py         tickets, returns, reports
    admin.py           internal operations console
  services/
    pricing.py         totals, coupons, GST
    shipping.py        courier booking and tracking
    notifications.py   SMS through MSG91
    search.py          catalogue search
  utils/
    logging.py         log format
    validators.py      phone, pincode, PAN, GST, IFSC, UPI, Aadhaar
```

## A note for anyone reading this repository

This is a teaching fixture, not a product. It is written to look like
an ordinary Indian marketplace backend at a few years of age, and it
carries the data protection gaps such a codebase usually carries: a
consent boolean instead of a consent record, personal data in the
application log, internal endpoints that trust the network, KYC
identifiers in clear text, no retention period on anything, and no
route by which a customer can be erased.

Nothing here is a strawman. Every gap in it is one that appears in
real code, usually for the reason written in the comment next to it.
It exists so a compliance scanner has something honest to find.
