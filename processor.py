import os
import pandas as pd
import numpy as np
from datetime import datetime
from fuzzywuzzy import fuzz

# Supported file formats
SUPPORTED_EXT = ['.csv', '.xls', '.xlsx']

# Shopify 53-column export format
SHOPIFY_HEADERS = [
    'Handle', 'Title', 'Body (HTML)', 'Vendor', 'Type', 'Tags', 'Published',
    'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value', 'Option3 Name', 'Option3 Value',
    'Variant SKU', 'Variant Grams', 'Variant Inventory Tracker', 'Variant Inventory Qty',
    'Variant Inventory Policy', 'Variant Fulfillment Service', 'Variant Price', 'Variant Compare At Price',
    'Variant Cost', 'Variant Requires Shipping', 'Variant Taxable', 'Variant Barcode',
    'Image Src', 'Image Position', 'Image Alt Text', 'Gift Card', 'SEO Title', 'SEO Description',
    'Google Shopping / Google Product Category', 'Google Shopping / Gender', 'Google Shopping / Age Group',
    'Google Shopping / MPN', 'Google Shopping / AdWords Grouping', 'Google Shopping / AdWords Labels',
    'Google Shopping / Condition', 'Google Shopping / Custom Product', 'Google Shopping / Custom Label 0',
    'Google Shopping / Custom Label 1', 'Google Shopping / Custom Label 2', 'Google Shopping / Custom Label 3',
    'Google Shopping / Custom Label 4', 'Variant Image', 'Variant Weight Unit', 'Variant Tax Code',
    'Cost per item', 'Price / International', 'Compare At Price / International', 'Status'
]

# Threshold for fuzzy matching column headers
FUZZY_THRESHOLD = 70

# Supplier column mapping to expected schema
DEFAULT_MAP = {
    'Model': ['Model', 'Product Name', 'Item Name'],
    'Voltage': ['Voltage', 'Power Spec'],
    'Power': ['Power HP', 'Horsepower'],
    'Weight': ['Weight lbs', 'Product Weight'],
    'List Price': ['List Price', 'Base Price'],
    'Article Number': ['Part Number', 'SKU', 'Item Code']
}

# Fuzzy match column headers
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

# Convert product name into Shopify-compatible handle
def sanitize_handle(name):
    return name.strip().lower().replace(' ', '-').replace('/', '-').replace('(', '').replace(')', '')

# Build HTML product description
def build_description(row, config):
    desc = f"<p><strong>Model:</strong> {row['Model']}<br>"
    desc += f"<strong>Voltage:</strong> {row['Voltage']}<br>"
    desc += f"<strong>Power:</strong> {row['Power']} HP<br>"
    desc += f"<strong>Weight:</strong> {row['Weight']} lbs</p>"
    if float(row['Weight']) > config['weight_threshold']:
        desc += '<p><em>NOTE: We will contact you during order fulfilment to discuss shipping and handling costs for products weighing more than 150 pounds. These costs will be billed separately.</em></p>'
    desc += '<p><a href="https://wilo.com/en/overview.html" target="_blank">View on Manufacturer Website</a></p>'
    return desc

# Main function to process the supplier file
def process_file(filepath, config, mode):
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXT:
        raise Exception("Unsupported file format.")

    df = pd.read_excel(filepath) if ext in ['.xls', '.xlsx'] else pd.read_csv(filepath)
    if len(df) > 1000:
        print("Warning: File has more than 1000 rows.")

    column_map = fuzzy_match_columns(df)
    df = df.rename(columns=column_map)

    rows = []
    errors = []
    used_handles = set()

    for idx, row in df.iterrows():
        try:
            model = str(row['Model']).strip()
            voltage = str(row['Voltage']).strip()
            power = row['Power']

            # Validate and convert weight
            try:
                weight_raw = str(row['Weight']).strip()
                if weight_raw in ['—', '-', '', 'N/A']:
                    raise ValueError("Invalid or missing weight")
                weight = float(weight_raw)
            except:
                raise Exception(f"Row {idx+1}: Invalid or missing weight")

            # Validate SKU
            part_number = str(row['Article Number']).strip()
            if part_number in ['—', '-', '', 'N/A']:
                raise Exception(f"Row {idx+1}: Invalid or missing SKU")

            # Pricing
            list_price = float(row['List Price']) if pd.notna(row['List Price']) and str(row['List Price']).strip() else 0.0
            price = config['pricing_formula'](list_price)
            cost = config['cost_formula'](list_price)

            # Build product fields
            title = f"{model} ({voltage})"
            handle = sanitize_handle(model)
            description = build_description(row, config)
            requires_shipping = 'FALSE' if weight > config['weight_threshold'] else 'TRUE'

            # Ensure handle is not reused
            if handle in used_handles:
                raise Exception(f"Row {idx+1}: Duplicate handle detected: {handle}")
            used_handles.add(handle)

            # Build row
            shopify_row = {
                'Handle': handle,
                'Title': title,
                'Body (HTML)': description if mode == 'full' else '',
                'Vendor': config['vendor'],
                'Type': config['product_type'],
                'Tags': '',
                'Published': 'FALSE',
                'Option1 Name': 'Voltage',
                'Option1 Value': voltage,
                'Option2 Name': '',
                'Option2 Value': '',
                'Option3 Name': '',
                'Option3 Value': '',
                'Variant SKU': part_number,
                'Variant Grams': int(round(weight * 453.592)),
                'Variant Inventory Tracker': 'shopify',
                'Variant Inventory Qty': '',
                'Variant Inventory Policy': 'deny',
                'Variant Fulfillment Service': 'manual',
                'Variant Price': price,
                'Variant Compare At Price': list_price,
                'Variant Cost': cost,
                'Variant Requires Shipping': requires_shipping,
                'Variant Taxable': 'TRUE',
                'Variant Barcode': '',
                'Image Src': config['image_url'],
                'Image Position': 1,
                'Image Alt Text': title,
                'Gift Card': 'FALSE',
                'SEO Title': title,
                'SEO Description': f"Buy {title} online.",
                'Google Shopping / Google Product Category': '',
                'Google Shopping / Gender': '',
                'Google Shopping / Age Group': '',
                'Google Shopping / MPN': part_number,
                'Google Shopping / AdWords Grouping': '',
                'Google Shopping / AdWords Labels': '',
                'Google Shopping / Condition': 'new',
                'Google Shopping / Custom Product': 'TRUE',
                'Google Shopping / Custom Label 0': '',
                'Google Shopping / Custom Label 1': '',
                'Google Shopping / Custom Label 2': '',
                'Google Shopping / Custom Label 3': '',
                'Google Shopping / Custom Label 4': '',
                'Variant Image': config['image_url'],
                'Variant Weight Unit': 'lb',
                'Variant Tax Code': '',
                'Cost per item': cost,
                'Price / International': '',
                'Compare At Price / International': '',
                'Status': 'draft'
            }

            if mode == 'description-only':
                shopify_row = {
                    'Handle': handle,
                    'Body (HTML)': description
                }

            rows.append(shopify_row)

        except Exception as e:
            errors.append(str(e))

    if not rows:
        raise Exception("No valid rows to export.")

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    outdir = "exports"
    os.makedirs(outdir, exist_ok=True)

    if mode == 'description-only':
        out_file = os.path.join(outdir, f"shopify_descriptions_{ts}.csv")
        pd.DataFrame(rows).to_csv(out_file, index=False)
    else:
        out_file = os.path.join(outdir, f"shopify_import_{ts}.csv")
        pd.DataFrame(rows, columns=SHOPIFY_HEADERS).to_csv(out_file, index=False)

    if errors:
        error_log = os.path.join(outdir, f"errors_{ts}.log")
        with open(error_log, 'w') as f:
            for e in errors:
                f.write(e + '\n')
        print(f"⚠️ Validation errors logged to {error_log}")

    return out_file
