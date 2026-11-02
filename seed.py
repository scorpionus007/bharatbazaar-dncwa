"""Fill the catalogue so the storefront has something to show.

    python seed.py

Idempotent: it clears the catalogue tables and rebuilds them, and
leaves customers and orders alone.
"""

from app.database import Base, SessionLocal, engine
from app.models.catalog import Category, Product, Review
from app.models.seller import Seller

CATEGORIES = [
    ("Electronics", "electronics", "8517", 18.0),
    ("Kitchen", "kitchen", "7323", 12.0),
    ("Fashion", "fashion", "6109", 5.0),
    ("Grocery", "grocery", "0910", 5.0),
    ("Home", "home", "9404", 12.0),
    ("Books", "books", "4901", 0.0),
]

SELLERS = [
    ("Shree Krishna Electronics Pvt Ltd", "Shree Krishna Electronics"),
    ("Annapurna Homewares LLP", "Annapurna Homewares"),
    ("Rangoli Apparels Private Limited", "Rangoli Apparels"),
]

# (category slug, title, brand, mrp, price, stock, description)
PRODUCTS = [
    ("electronics", "Redmi Note 14 5G (Mystic Blue, 128 GB)", "Redmi", 18999, 14499, 42,
     "6.67 inch AMOLED, 50MP camera, 5110mAh battery with 45W fast charging."),
    ("electronics", "boAt Airdopes 311 Pro Wireless Earbuds", "boAt", 4490, 1299, 180,
     "Up to 50 hours playback, ENx noise cancellation, IPX4 splash resistant."),
    ("electronics", "Mi Power Bank 3i 20000mAh", "Mi", 2499, 1799, 95,
     "Dual output, 18W fast charging, triple layer protection."),
    ("electronics", "Noise ColorFit Pro 5 Smart Watch", "Noise", 5999, 2499, 60,
     "1.85 inch display, Bluetooth calling, 100 sports modes."),
    ("electronics", "Zebronics Zeb-Thunder Wireless Headphone", "Zebronics", 1999, 849, 140,
     "60 hour backup, 40mm drivers, built in FM and microSD slot."),

    ("kitchen", "Prestige Omega Deluxe Granite Kadai 24cm", "Prestige", 2195, 1349, 75,
     "Five layer granite non stick coating, induction and gas compatible."),
    ("kitchen", "Hawkins Contura Pressure Cooker 3 Litre", "Hawkins", 2550, 1899, 50,
     "Hard anodised, curved body for easy stirring, five year guarantee."),
    ("kitchen", "Milton Thermosteel Flip Lid Flask 1000ml", "Milton", 1795, 1099, 120,
     "Keeps liquids hot or cold for 24 hours, 18/8 stainless steel."),
    ("kitchen", "Butterfly Smart Mixer Grinder 750W", "Butterfly", 4690, 2799, 38,
     "Three stainless steel jars, overload protector, two year warranty."),
    ("kitchen", "Borosil Glass Mixing Bowl Set of 3", "Borosil", 1250, 799, 88,
     "Oven and microwave safe borosilicate glass, nested storage."),

    ("fashion", "Allen Solly Men Regular Fit Cotton Shirt", "Allen Solly", 2299, 1149, 64,
     "Pure cotton, full sleeve, machine washable, available in six colours."),
    ("fashion", "Biba Women Printed Straight Kurta", "Biba", 1999, 1199, 52,
     "Rayon blend, three quarter sleeve, side slits, knee length."),
    ("fashion", "Campus Sutra Men Hooded Sweatshirt", "Campus Sutra", 1799, 749, 98,
     "Fleece lined, kangaroo pocket, ribbed cuffs."),
    ("fashion", "Bata Comfit Men Formal Derby Shoes", "Bata", 2499, 1599, 41,
     "Cushioned insole, synthetic upper, slip resistant sole."),

    ("grocery", "Tata Sampann Unpolished Toor Dal 1kg", "Tata Sampann", 220, 179, 300,
     "Unpolished, higher protein retention, no artificial colour."),
    ("grocery", "Aashirvaad Shudh Chakki Atta 10kg", "Aashirvaad", 560, 479, 210,
     "100 percent whole wheat, no maida, chakki ground."),
    ("grocery", "Everest Garam Masala 100g", "Everest", 95, 82, 400,
     "Blend of 15 spices, ground fresh, resealable pack."),
    ("grocery", "Saffola Gold Refined Cooking Oil 5L", "Saffola", 1150, 949, 160,
     "Blend of rice bran and sunflower oil, LOSORB technology."),

    ("home", "Solimo 3 Seater Fabric Sofa Cover", "Solimo", 1499, 699, 70,
     "Stretchable polyester spandex, machine washable, anti slip foam."),
    ("home", "Wakefit Orthopaedic Memory Foam Pillow", "Wakefit", 1599, 849, 110,
     "Medium firm, breathable cover, three year warranty."),
    ("home", "Philips 9W LED Bulb Pack of 4", "Philips", 760, 449, 240,
     "Cool day light, 900 lumens, two year replacement warranty."),

    ("books", "The White Tiger", "HarperCollins", 399, 229, 85,
     "Aravind Adiga. Winner of the Man Booker Prize."),
    ("books", "Wings of Fire: An Autobiography", "Universities Press", 350, 199, 130,
     "A P J Abdul Kalam with Arun Tiwari."),
    ("books", "India After Gandhi", "Picador India", 899, 599, 46,
     "Ramachandra Guha. The history of the world's largest democracy."),
]

REVIEWS = [
    (1, 5, "Excellent phone for the price", "Battery lasts two days easily.", "Ananya S."),
    (1, 4, "Good but heats a little", "Camera is sharp in daylight.", "Rakesh M."),
    (2, 4, "Solid earbuds", "Bass is strong, calls are clear.", "Priya K."),
    (6, 5, "Non stick coating is genuine", "Nothing sticks even without oil.", "Lakshmi V."),
    (7, 5, "Hawkins never disappoints", "Third cooker from them.", "Suresh N."),
    (15, 5, "Good quality dal", "Cooks fast, no stones.", "Meera J."),
    (22, 5, "A must read", "Finished it in two sittings.", "Arjun P."),
]


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(Review).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(Seller).delete()
        db.commit()

        sellers = []
        for legal, display in SELLERS:
            seller = Seller(
                legal_name=legal,
                display_name=display,
                contact_phone="98" + str(10000000 + len(sellers)),
                contact_email=f"seller{len(sellers)}@example.in",
                gst_number="27AAPFU0939F1ZV",
                pan_number="AAPFU0939F",
                aadhaar_number="999988887777",
                bank_account_number="50100123456789",
                bank_ifsc="HDFC0001234",
                account_holder_name=legal,
                pickup_pincode="400001",
            )
            db.add(seller)
            sellers.append(seller)
        db.commit()

        by_slug = {}
        for name, slug, hsn, gst in CATEGORIES:
            category = Category(name=name, slug=slug, hsn_code=hsn, gst_rate=gst)
            db.add(category)
            by_slug[slug] = category
        db.commit()

        for index, (slug, title, brand, mrp, price, stock, blurb) in enumerate(PRODUCTS):
            db.add(
                Product(
                    seller_id=sellers[index % len(sellers)].id,
                    category_id=by_slug[slug].id,
                    title=title,
                    brand=brand,
                    description=blurb,
                    sku=f"BB-{slug[:3].upper()}-{index + 1:04d}",
                    mrp=mrp,
                    selling_price=price,
                    stock_quantity=stock,
                )
            )
        db.commit()

        products = db.query(Product).order_by(Product.id).all()
        for position, rating, title, body, who in REVIEWS:
            if position <= len(products):
                db.add(
                    Review(
                        product_id=products[position - 1].id,
                        customer_id=None,
                        rating=rating,
                        title=title,
                        body=body,
                        reviewer_display_name=who,
                        is_verified_purchase=True,
                    )
                )
        db.commit()

        print(
            f"seeded {len(CATEGORIES)} categories, "
            f"{len(PRODUCTS)} products, {len(REVIEWS)} reviews"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
