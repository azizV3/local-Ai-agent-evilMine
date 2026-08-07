'''  


  {
        "type": "function",
        "function": {
            "name": "get_product_info",
            "description": "Get detailed information about a GlobalJava Roasters product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_products",
            "description": "List all product ids before using get_product_info if unsure of exact id."
        }
    },
 '''
PRODUCTS = {
    "ethiopian-yirgacheffe": {
        "name": "Ethiopian Yirgacheffe Single-Origin",
        "origin": "Yirgacheffe region, Ethiopia",
        "flavor_profile": "Bright citrus, floral aroma, light body",
        "price": 18.99,
        "certifications": ["Fair Trade", "Organic"]
    },
    "house-blend": {
        "name": "GlobalJava House Blend",
        "origin": "Colombia and Brazil blend",
        "flavor_profile": "Balanced, chocolatey, nutty",
        "price": 12.99,
        "certifications": []
    },
    "geisha-reserve": {
        "name": "Limited Edition Geisha Reserve",
        "origin": "Hacienda La Esmeralda, Panama",
        "flavor_profile": "Jasmine, bergamot, white peach",
        "price": 89.99,
        "certifications": ["Single Estate", "Competition Grade"]
    }
}

def get_product_info(product_id: str) -> dict:
    """Look up product information by ID."""
    if product_id not in PRODUCTS:
        return {"error": f"Product '{product_id}' not found"}
    return PRODUCTS[product_id]

def list_all_products() -> dict:

    dict_keys = {key: key for key in PRODUCTS}
    return(dict_keys)

def funny_function() -> str:

    return "something funny"