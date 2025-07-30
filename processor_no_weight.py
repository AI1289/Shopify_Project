import os
import pandas as pd
import numpy as np
from datetime import datetime
from fuzzywuzzy import fuzz
from description import generate_description

SUPPORTED_EXT = ['.csv', '.xls', '.xlsx']

SHOPIFY_HEADERS = [
    'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Type', 'Tags', 'Published',
    'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value',
    'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty',
    'Variant Inventory Policy', 'Variant Fulfillment Service', 'Variant Price', 'Variant Compare At Price',
    'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode', 'Product Category',
    'Image Src', 'Image Position', 'Image Alt Text', 'Gift Card', 'SEO Title', 'SEO Description',
    'Google Shopping / Google Product Category', 'Google Shopping / Gender', 'Google Shopping / Age Group',
    'Google Shopping / MPN', 'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels',
    'Google Shopping / Condition', 'Google Shopping / Custom Product', 'Google Shopping / Custom Label 0',
    'Google Shopping / Custom Label 1', 'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3',
    'Google Shopping / Custom Label 4', 'Variant Image', 'Variant Weight Unit', 'Variant Tax Code',
    'Cost per item', 'Price / International', 'Compare At Price / International', 'Status'
]

FUZZY_THRESHOLD = 70

DEFAULT_MAP = {
    'Model': ['Model'],
    'Voltage': ['Voltage'],
    'Power': ['Power HP', 'Individual Pump Power (HP)'],
    'Weight': ['Weight lbs'],
    'List Price': ['List Price'],
    'Article Number': ['Article Number', 'Part Number']
}

def generate_shopify_sku(row, config, option_fields_key="variant_option_fields"):
    """
    Build a globally unique SKU from product type, model, and all option values.
    Cleans up spaces and punctuation for a Shopify-friendly SKU.

    Args:
        row (dict or pd.Series): The source row data.
        config (dict): The current formulas/config, must include variant_option_fields.
        option_fields_key (str): Key in config for option fields.

    Returns:
        str: Unique, uppercase SKU string.
    """
    def clean(val):
        # Remove spaces, brackets, slashes, dashes, and make uppercase
        return str(val).replace(' ', '').replace('(', '').replace(')', '').replace('&', '').replace('/', '').replace('-', '').upper()

    sku_parts = []

    # 1. Product Type
    prod_type = row.get('Type', '')
    if pd.notnull(prod_type) and str(prod_type).strip():
        sku_parts.append(clean(prod_type))

    # 2. Model
    model = row.get('Model', '')
    if pd.notnull(model) and str(model).strip():
        sku_parts.append(clean(model))

    # 3. Variant options (from config)
    option_fields = config.get(option_fields_key, [])
    for field in option_fields:
        val = row.get(field, "")
        if pd.notnull(val) and str(val).strip().upper() not in ("", "CF", "N/A", "—", "-"):
            sku_parts.append(clean(val))

    # 4. Join for final SKU
    return "-".join(sku_parts)

# --- USAGE IN YOUR EXPORT LOOP ---
# row_dict['Variant SKU'] = generate_shopify_sku(row, config)

def safe_eval(expr, context):
    import ast
    try:
        tree = ast.parse(expr, mode='eval')
        allowed = (
            ast.Expression, ast.BinOp, ast.Num, ast.Name, ast.Load, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
            ast.Call, ast.FormattedValue, ast.JoinedStr, ast.Constant
        )
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise ValueError(f"Unsafe expression: {expr} [blocked {type(node).__name__}]")
        return eval(compile(tree, "<string>", "eval"), {}, context)
    except Exception as e:
        raise ValueError(f"Invalid formula: {e}")

def fuzzy_match_columns(df):
    mapping = {}
    for key, aliases in DEFAULT_MAP.items():
        for alias in aliases:
            for col in df.columns:
                score = fuzz.token_set_ratio(col.lower(), alias.lower())
                if score >= FUZZY_THRESHOLD:
                    mapping[key] = col
                    break
            if key in mapping:
                break
    missing = [key for key in DEFAULT_MAP if key not in mapping]
    if missing:
        raise Exception(f"Missing required columns: {missing}")
    return mapping

def sanitize_handle(name):
    return name.strip().lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')

def process_file(filepath, config, mode):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXT:
        raise Exception("Unsupported file format.")

    df = pd.read_excel(filepath) if ext in ['.xls', '.xlsx'] else pd.read_csv(filepath)
    if len(df) > 1500:
        print("Warning: File has more than 1500 rows.")

    column_map = fuzzy_match_columns(df)
    df = df.rename(columns=column_map)

    col_model = column_map['Model']
    col_voltage = column_map['Voltage']
    col_power = column_map['Power']
    col_weight = column_map['Weight']
    col_price = column_map['List Price']
    col_sku = column_map['Article Number']

    rows = []
    errors = []

    grouped = df.groupby(col_model)
    for model, group in grouped:
        valid_rows = []
        for idx in range(len(group)):
            row = group.iloc[idx]
            part_number = str(row[col_sku]).strip()
            price_raw = str(row[col_price]).strip()
            # Skip any row with 'CF', '-', '', 'N/A', or '—' as price or part_number
            if price_raw in ['—', '-', '', 'N/A', 'CF']:
                list_price = 0.0
            else:
                try:
                    list_price = float(price_raw)
                except:
                    list_price = 0.0

            if part_number in ['—', '-', '', 'N/A', 'CF'] or not list_price:
                continue
            valid_rows.append(idx)
        if not valid_rows:
            continue

        handle = sanitize_handle(model)
        for i, row_idx in enumerate(valid_rows):
            row = group.iloc[row_idx]
            voltage = str(row[col_voltage]).strip()
            part_number = str(row[col_sku]).strip()
            # Digital product: forcibly set weight and grams to 0
            weight = 0.0
            grams = 0
            try:
                list_price = float(row[col_price]) if pd.notna(row[col_price]) and str(row[col_price]).strip() else 0.0
            except:
                list_price = 0.0

            price = safe_eval(config.get('pricing_formula', 'list_price * 0.36 * 1.15'), {'list_price': list_price})
            cost = safe_eval(config.get('cost_formula', 'list_price * 0.36'), {'list_price': list_price})

            title = f"{model}"
            # --- Build unified context for all formulas ---
            row_context = dict(row)
            if config:
                row_context.update({k: v for k, v in config.items()})
            row_context['price'] = price
            row_context['grams'] = grams
            row_context['cost'] = cost
            row_context['title'] = title
            row_context['model'] = model
            row_context['voltage'] = voltage
            row_context['description'] = ''  # Placeholder
                # --- Generate description and update context ---
            description = generate_description(row_context, config.get('seo_description_formula'), config)
            row_context['description'] = description

            # --- SEO fields use same context ---
            seo_title = safe_eval(config.get('seo_title_formula'), row_context)
            seo_description = safe_eval(config.get('seo_description_formula'), row_context)

            # Digital: Requires Shipping always FALSE
            requires_shipping = 'FALSE'

            row_dict = {
                'Handle': handle,
                'Title': title,
                'Body (HTML)': description if mode == 'full' else '',
                'Vendor': config['vendor'],
                'Type': config['product_type'],
                'Tags': f"{config['vendor']}, {config['collection']}-{voltage}",
                'Published': 'FALSE',
                'Option1 Name': '',
                'Option1 Value': '',
                'Option2 Name': '',
                'Option2 Value': '',
                'Option3 Name': '',
                'Option3 Value': '',
                'Variant SKU': part_number,
                'Variant Grams': grams,
                'Variant Inventory Tracker': '',
                'Variant Inventory Qty': '',
                'Variant Inventory Policy': 'continue',
                'Variant Fulfillment Service': 'manual',
                'Variant Price': price,
                'Variant Compare At Price': list_price,
                'Variant Requires Shipping': requires_shipping,
                'Variant Taxable': 'TRUE',
                'Variant Barcode': '',
                'Product Category': config.get('product_category', ''),
                'Image Src': config['image_url'] if i == 0 else '',
                'Image Position': 1 if i == 0 else '',
                'Image Alt Text': title if i == 0 else '',
                'SEO Title': seo_title,
                'SEO Description': seo_description,
                'Google Shopping / Gender': '',
                'Google Shopping / Age Group': '',
                'Google Shopping / AdWords Grouping': '',
                'Google Shopping / AdWords Labels': '',
                'Google Shopping / Custom Label 0': '',
                'Google Shopping / Custom Label 1': '',
                'Google Shopping / Custom Label 2': '',
                'Google Shopping / Custom Label 3': '',
                'Google Shopping / Custom Label 4': '',
                'Variant Image': config['image_url'] if i == 0 else '',
                'Variant Weight Unit': 'lb',
                'Variant Tax Code': '',
                'Cost per item': cost,
                'Price / International': '',
                'Compare At Price / International': '',
                'Status': 'draft'
            }

            if mode == 'description-only':
                row_dict = {
                    'Handle': handle,
                    'Body (HTML)': description
                }
            # --- DYNAMIC VARIANT LOGIC BELOW ---
            option_fields = config.get("variant_option_fields", ["Power HP", "Voltage"])

            # Build option values, treating blanks/invalids as empty
            option_values = []
            for field in option_fields:
                val = row.get(field, "")
                if pd.isnull(val) or str(val).strip().upper() in ("", "CF", "N/A", "—", "-"):
                    val = ""
                option_values.append(val)

            # If ALL option values are blank, treat as single product (no variants)
            if all(v == "" for v in option_values):
                for idx in range(3):
                    row_dict[f'Option{idx+1} Name'] = ''
                    row_dict[f'Option{idx+1} Value'] = ''
            else:
                # Option1 (first) must NOT be blank, otherwise skip this variant
                if option_values[0] == "":
                    continue  # skip this variant

                # Option2 and Option3 CAN be blank!
                for idx in range(3):
                    opt_num = idx + 1
                    row_dict[f'Option{opt_num} Name'] = option_fields[idx] if idx < len(option_fields) else ''
                    row_dict[f'Option{opt_num} Value'] = option_values[idx] if idx < len(option_values) else ''
            # --- END VARIANT LOGIC ---

            # Using SKU Logic
            if part_number in ("", "CF", "N/A", "—", "-") or pd.isnull(part_number):
                row_dict['Variant SKU'] = generate_shopify_sku(row, config)
            else:
                row_dict['Variant SKU'] = part_number
            # Add to rows
            rows.append(row_dict)

    if not rows:
        raise Exception("No valid rows to export.")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    outdir = "exports"
    os.makedirs(outdir, exist_ok=True)

    out_file = os.path.join(outdir, f"shopify_import_{ts}.csv") if mode == 'full' \
        else os.path.join(outdir, f"shopify_descriptions_{ts}.csv")

    columns = SHOPIFY_HEADERS if mode == 'full' else ['Handle', 'Body (HTML)']
    pd.DataFrame(rows, columns=columns).to_csv(out_file, index=False)

    if errors:
        error_log = os.path.join(outdir, f"errors_{ts}.log")
        with open(error_log, 'w') as f:
            for e in errors:
                f.write(e + '\n')
        print(f"⚠️ Validation errors logged to {error_log}")

    return out_file
