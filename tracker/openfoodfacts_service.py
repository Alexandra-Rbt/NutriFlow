"""
NutriFlow — Serviciu de integrare Open Food Facts
"""

import logging
import openfoodfacts

logger = logging.getLogger(__name__)

_api = openfoodfacts.API(user_agent="NutriFlow/1.0")

CATEGORY_MAP = {
    "en:meats":      "protein",
    "en:fish":       "protein",
    "en:seafood":    "protein",
    "en:eggs":       "protein",
    "en:legumes":    "protein",
    "en:dairy":      "dairy",
    "en:cheeses":    "dairy",
    "en:yogurts":    "dairy",
    "en:milks":      "dairy",
    "en:cereals":    "grain",
    "en:pastas":     "grain",
    "en:breads":     "grain",
    "en:rice":       "grain",
    "en:vegetables": "vegetable",
    "en:fruits":     "fruit",
    "en:fats":       "fat",
    "en:oils":       "fat",
    "en:snacks":     "snack",
    "en:beverages":  "drink",
    "en:drinks":     "drink",
    "en:waters":     "drink",
}


def _detect_category(categories_tags: list) -> str:
    if not categories_tags:
        return "other"
    for tag in categories_tags:
        tag_lower = tag.lower()
        for key, cat in CATEGORY_MAP.items():
            if key in tag_lower:
                return cat
    return "other"


def _safe_float(value, default=0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _extract_nutrition(nutriments: dict) -> dict:
    kcal = nutriments.get("energy-kcal_100g")
    if not kcal:
        kj = nutriments.get("energy_100g", 0)
        kcal = float(kj) / 4.184 if kj else 0
    return {
        "kcal":    _safe_float(kcal),
        "protein": _safe_float(nutriments.get("proteins_100g", 0)),
        "carbs":   _safe_float(nutriments.get("carbohydrates_100g", 0)),
        "fat":     _safe_float(nutriments.get("fat_100g", 0)),
        "fiber":   _safe_float(nutriments.get("fiber_100g", 0)),
    }


def _product_to_dict(product) -> dict | None:
    # SDK v5 returneaza obiecte Pydantic — convertim la dict
    if hasattr(product, 'model_dump'):
        product = product.model_dump()
    elif not isinstance(product, dict):
        try:
            product = dict(product)
        except Exception:
            return None

    nutriments = product.get("nutriments") or {}
    if not isinstance(nutriments, dict):
        try:
            nutriments = dict(nutriments)
        except Exception:
            return None

    if not nutriments:
        return None

    nutrition = _extract_nutrition(nutriments)
    if nutrition["kcal"] == 0 and nutrition["protein"] == 0:
        return None

    name = (
        product.get("product_name_ro")
        or product.get("product_name")
        or product.get("product_name_en")
        or ""
    )
    if not name or not str(name).strip():
        return None
    name = str(name).strip()

    brand = str(product.get("brands", "") or "")
    if brand:
        first_brand = brand.split(",")[0].strip()
        if first_brand and first_brand.lower() not in name.lower():
            name = f"{name} ({first_brand})"

    categories_tags = product.get("categories_tags") or []
    if not isinstance(categories_tags, list):
        categories_tags = []

    return {
        "off_code":  str(product.get("code", "") or product.get("_id", "") or ""),
        "name":      name[:200],
        "category":  _detect_category(categories_tags),
        "kcal":      nutrition["kcal"],
        "protein":   nutrition["protein"],
        "carbs":     nutrition["carbs"],
        "fat":       nutrition["fat"],
        "fiber":     nutrition["fiber"],
        "image_url": str(product.get("image_front_small_url", "") or ""),
        "quantity":  str(product.get("quantity", "") or ""),
    }


def search_foods(query: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """Cauta alimente in OFF — compatibil SDK v5 (fara parametrul fields)."""
    try:
        result = _api.product.text_search(
            query,
            page=page,
            page_size=page_size,
        )
        if hasattr(result, 'products'):
            products = result.products or []
        elif isinstance(result, dict):
            products = result.get("products", [])
        else:
            products = []

        parsed = []
        for p in products:
            try:
                data = _product_to_dict(p)
                if data:
                    parsed.append(data)
            except Exception as e:
                logger.debug("Skip produs: %s", e)
        return parsed
    except Exception as e:
        logger.error("Eroare cautare OFF '%s': %s", query, e)
        return []


def get_product_by_barcode(barcode: str) -> dict | None:
    """Cauta produs dupa cod de bare EAN — compatibil SDK v5."""
    try:
        product = _api.product.get(barcode)
        if not product:
            return None
        return _product_to_dict(product)
    except Exception as e:
        logger.error("Eroare barcode OFF '%s': %s", barcode, e)
        return None


def import_product_to_db(product_data: dict, user=None):
    """
    Salveaza un produs in baza de date.
    Returneaza (food_object, created: bool).
    Nu dubleaza dupa off_code sau nume.
    """
    from .models import Food

    off_code = product_data.get("off_code", "") or ""

    if off_code:
        existing = Food.objects.filter(off_code=off_code).first()
        if existing:
            return existing, False

    existing = Food.objects.filter(name=product_data["name"]).first()
    if existing:
        return existing, False

    food = Food.objects.create(
        name             = product_data["name"],
        category         = product_data.get("category", "other"),
        kcal_per_100g    = product_data["kcal"],
        protein_per_100g = product_data.get("protein", 0),
        carbs_per_100g   = product_data.get("carbs", 0),
        fat_per_100g     = product_data.get("fat", 0),
        fiber_per_100g   = product_data.get("fiber", 0),
        off_code         = off_code,
        is_custom        = False,
        created_by       = user,
    )
    return food, True