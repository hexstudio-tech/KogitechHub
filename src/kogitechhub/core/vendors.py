VENDORS = {
    "046d": "Logitech",
    "03f0": "HP",
    "1532": "Razer",
    "1038": "SteelSeries",
    "045e": "Microsoft",
    "093a": "Pixart",
    "258a": "SINO WEALTH",
    "0b05": "ASUS",
    "04d9": "Holtek",
    "413c": "Dell",
    "17ef": "Lenovo",
    "1e7d": "Roccat",
    "046a": "Cherry",
    "05ac": "Apple",
}


def vendor_name(vendor_id: str) -> str:
    return VENDORS.get((vendor_id or "").lower(), "")
