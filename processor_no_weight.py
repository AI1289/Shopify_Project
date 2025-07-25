# processor_no_weight.py
#
# Shopify Import File Generator
# Transforms supplier Excel/CSV data into a valid Shopify import CSV
# with support for pricing formulas, SEO logic, variant grouping, and error handling.
# Branch 2 (processor_no_weight.py)
# Weight is being Set to 0 and Removed from Body and Requires Shipping is False to make it into a Digital Product

import os
import pandas as pd
import numpy as np
from datetime import datetime
from fuzzywuzzy import fuzz

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

SUPPORTED_EXT = ['.csv', '.xls', '.xlsx']

SHOPIFY_HEADERS = [
    'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Type', 'Tags', 'Published',
    'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value',
    'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty',
    'Variant Inventory Policy', 'Variant Fulfillment Service',
    'Variant Price', 'Variant Compare At Price',
    'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode',
    'Product Category',
    'Image Src', 'Image Position', 'Image Alt Text', 'Gift Card',
    'SEO Title', 'SEO Description',
    'Google Shopping / Google Product Category', 'Google Shopping / Gender', 'Google Shopping / Age Group',
    'Google Shopping / MPN', 'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels',
    'Google Shopping / Condition', 'Google Shopping / Custom Product',
    'Google Shopping / Custom Label 0', 'Google Shopping / Custom Label 1',
    'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3', 'Google Shopping / Custom Label 4',
    'Variant Image', 'Variant Weight Unit', 'Variant Tax Code',
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

def build_description(row, config, col_model, col_voltage, col_power, col_weight):
    desc = f"<p><strong>Model: </strong> {row[col_model]}<br>"
    desc += f"<strong>Voltage: </strong> {row[col_voltage]}<br>"
    desc += f"<strong>Power: </strong> {row[col_power]} HP<br>"
    # desc += f"<strong>Weight: </strong> {row[col_weight]} lbs</p>"

    desc += '<p><em>NOTE: We will contact you during order fulfilment to discuss shipping and handling costs for products weighing more than 150 pounds. These costs will be billed separately.</em></p>'
    desc += '<p><a href="https://wilo.com/en/overview.html" target="_blank">View Manufacturer Website</a></p>'
    return desc

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

    grouped = df.groupby('Model')
    for model, group in grouped:
        valid_rows = []
        for idx in range(len(group)):
            try:
                row = group.iloc[idx]
                # weight_raw = str(row[col_weight]).strip().replace(',', '')
                part_number = str(row[col_sku]).strip()

                # Compute list_price early
                try:
                    list_price = float(row[col_price]) if pd.notna(row[col_price]) and str(row[col_price]).strip() else 0.0
                except:
                    list_price = 0.0

                if  part_number in ['—', '-', '', 'N/A', 'CF'] or not list_price:
                    print(f"⚠️ Skipping row: part number, or list price → SKU: {part_number}, Price: {list_price}")
                    continue
                valid_rows.append(idx)
            except:
                continue
        if not valid_rows:
            continue

        handle = sanitize_handle(model)
        for i, row_idx in enumerate(valid_rows):
            row = group.iloc[row_idx]
            voltage = str(row[col_voltage]).strip()
            # weight_raw = str(row[col_weight]).strip().replace(',', '')
            part_number = str(row[col_sku]).strip()

            try:
                list_price = float(row[col_price]) if pd.notna(row[col_price]) and str(row[col_price]).strip() else 0.0
            except:
                list_price = 0.0

            price = safe_eval(config.get('pricing_formula', 'list_price * 0.36 * 1.21'), {'list_price': list_price})
            cost = safe_eval(config.get('cost_formula', 'list_price * 0.36'), {'list_price': list_price})

            # grams = safe_eval(config.get('grams_formula', 'int(round(weight * 453.592))'), {'weight': weight})
            # grams = int(round(int(row[col_weight]) * 453.592))
            # grams = int(round(float(row[col_weight]) * 453.592))
            grams = 0


            title = f"{model}"
            description = build_description(row, config, col_model, col_voltage, col_power, col_weight)

            context = {
                'collection': config['collection'],
                'model': model,
                'vendor': config['vendor'],
                'voltage': voltage,
                'description': description,
                'price': price
            }
            seo_title = safe_eval(config.get('seo_title_formula'), context)
            seo_description = safe_eval(config.get('seo_description_formula'), context)

            vendor_name = safe_eval(config.get('vendor_formula', "'{vendor}'"), {'vendor': config['vendor']})
            product_type = safe_eval(config.get('product_type_formula', "'{product_type}'"), {'product_type': config['product_type']})

            requires_shipping = 'FALSE' #if weight > config['weight_threshold'] else 'TRUE'

            row_dict = {
                'Handle': handle,
                'Title': title,
                'Body (HTML)': description if mode == 'full' else '',
                'Vendor': vendor_name,
                'Type': product_type,
                'Tags': f"{config['vendor']}, {config['collection']}-{voltage}",
                'Published': 'FALSE',
                'Option1 Name': 'Voltage',
                'Option1 Value': voltage,
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
                'Image Alt Text': '' if i > 0 else title,
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
