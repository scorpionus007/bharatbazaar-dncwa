# BharatBazaar

A marketplace, front to back. Customers sign in with a phone number
and an OTP, browse a catalogue, add to a cart, check out against a
saved address, pay through Razorpay and track the parcel through
Delhivery or Bluedart. Sellers onboard with a GST number and a KYC
pack and are settled weekly.

It runs. There is a storefront at `/`, not just an API.

## Running it

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe seed.py
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8200
```

Then open <http://localhost:8200>. SQLite by default, so there is no
database to stand up first; set `DATABASE_URL` for Postgres.

Create an account at `/register`, then sign in at `/login`. This is a
demo build, so the OTP is printed on the sign-in page instead of being
sent by SMS.

## What is worth clicking

| Page | What it shows |
|---|---|
| `/` | Catalogue, deals, categories |
| `/p/1` | Product detail with reviews |
| `/cart` and `/checkout` | Cart, GST, coupons, cash on delivery |
| `/account/privacy` | Everything held, who it is shared with, consents, nominee, deletion |
| `/support` | Grievance intake with a response deadline |
| `/internal/customers` | The operations console. No sign in. Look at this one. |

## Layout

```
app/
  config.py            environment and feature settings
  database.py          session wiring
  models/              customers, sellers, catalogue, orders, support
  api/                 the JSON API the mobile app talks to
  services/            pricing, shipping, notifications, search,
                       consent, retention, erasure, audit, processors
  web/storefront.py    the server rendered storefront
  utils/               logging, Indian format validators
templates/             Jinja2 pages
static/storefront.css  the stylesheet
seed.py                fills the catalogue
```

## What this repository is for

It is a teaching fixture for a DPDP Act compliance scanner, written to
look like an ordinary Indian marketplace backend at a few years of
age. It is neither a model implementation nor a strawman. Some
obligations are implemented properly and some are not, which is the
honest shape of real software and the only shape worth scanning.

### Implemented

- Consent recorded as an event with the purpose, the notice version
  and a timestamp, and withdrawal as a second row rather than an
  update (`app/services/consent.py`)
- Marketing consent off unless the box is ticked, and separate from
  the consent to run the account
- Access, in a page and a downloadable file (`/account/privacy/export`)
- Correction, through the account and address pages
- Erasure that cascades to addresses, saved cards, wishlist, browsing
  history and consents, anonymises reviews, and reduces the order to
  the invoice that tax law requires (`app/services/erasure.py`)
- Nomination under s.14
- A published list of every processor that receives personal data,
  rendered on the privacy page from `app/services/processors.py`
- Grievance intake with the s.13(2) clock on the row
- A retention period on every table holding personal data, and a
  nightly sweep that enforces it (`app/services/retention.py`)
- An audit trail, and a compliance report over it
- Storage in `ap-south-1`, so nothing leaves India

### Not implemented, deliberately

- **Seller KYC is stored in plaintext.** Aadhaar, PAN and bank account
  sit in clear columns. This is the worst thing in the repository.
- **The operations console at `/internal` has no authentication.** It
  returns every customer, exports them to CSV, and shows the seller
  KYC queue. The reasoning at the time was that it is only reachable
  over the office VPN.
- **The OTP and the phone number are written to the application log**,
  left over from the SMS integration work.
- **A date of birth is collected for birthday offers and never read.**
  Nothing evaluates age, so nothing can tell whether a customer is a
  child, and there is no guardian consent path at all.
- **No record of processing activities**, and no register for a
  direction of the Data Protection Board.
- **Erasure does not reach the logs.** The rows go; the log lines that
  copied them do not.

Each of those is a finding a scanner should produce, and each is in
real code for the reason written in the comment beside it.
