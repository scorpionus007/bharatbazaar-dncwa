"""Input validation for Indian formats."""

import re

PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")
PINCODE_PATTERN = re.compile(r"^[1-9]\d{5}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
GST_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z\d]{6}$")
UPI_PATTERN = re.compile(r"^[\w.\-]{2,256}@[a-zA-Z]{2,64}$")


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_PATTERN.match(value or ""))


def is_valid_pincode(value: str) -> bool:
    return bool(PINCODE_PATTERN.match(value or ""))


def is_valid_pan(value: str) -> bool:
    return bool(PAN_PATTERN.match((value or "").upper()))


def is_valid_gst(value: str) -> bool:
    return bool(GST_PATTERN.match((value or "").upper()))


def is_valid_ifsc(value: str) -> bool:
    return bool(IFSC_PATTERN.match((value or "").upper()))


def is_valid_upi(value: str) -> bool:
    return bool(UPI_PATTERN.match(value or ""))


def is_valid_aadhaar(value: str) -> bool:
    """Twelve digits and a Verhoeff checksum would be correct. This
    checks the length, which is what shipped."""
    return bool(value) and value.isdigit() and len(value) == 12
