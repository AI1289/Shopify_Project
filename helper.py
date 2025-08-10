import numpy as np
import pandas as pd

def validate_required_columns(df, config):
    required = config.get('required_columns', [])
    if not isinstance(required, list):
        raise Exception("Config error: 'required_columns' must be a list in formulas.json")
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise Exception(f"Missing required columns: {missing}\nColumns found: {list(df.columns)}\nColumns required (from config): {required}")

def is_invalid(val):
    if isinstance(val, str):
        return val.strip().upper() in ("", "CF", "N/A", "-", "—", "NAN")
    if pd.isna(val):
        return True
    return False

def get_variant_options(row, variant_option_fields):
    option_names = ["", "", ""]
    option_values = ["", "", ""]
    for idx, field in enumerate(variant_option_fields[:3]):
        val = row.get(field, "")
        if not is_invalid(val):
            option_names[idx] = field
            option_values[idx] = val
    return option_names, option_values

def generate_shopify_sku(row, config):
    formula = config.get("sku_formula")
    if formula:
        try:
            context = {k.lower().replace(" ", "_"): v for k, v in row.items()}
            return eval(formula, {}, context)
        except Exception:
            pass
    sku = str(row.get("Article Number", "")).strip()
    if not is_invalid(sku):
        return sku
    handle = str(row.get("Handle", "")).strip()
    variant_option_fields = config.get("variant_option_fields", [])
    options = [str(row.get(col, "")).strip() for col in variant_option_fields]
    sku = "-".join([handle] + [opt for opt in options if opt])
    return sku or "AUTO-SKU"
