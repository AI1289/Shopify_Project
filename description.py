import ast
import pandas as pd
import numpy as np

SHOPIFY_HEADERS = {
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
}

def safe_eval(expr: str, context: dict) -> str:
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.Num, ast.Name, ast.Load, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
        ast.Call, ast.FormattedValue, ast.JoinedStr, ast.Constant
    )
    try:
        tree = ast.parse(expr, mode='eval')
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Unsafe expression: {expr} [blocked {type(node).__name__}]")
        return eval(compile(tree, '<string>', 'eval'), {}, context)
    except Exception as e:
        return f"[Description Error: {e} in: {expr}]"

def generate_description(row: dict, seo_formula: str, config=None) -> str:
    if not config or 'description_include_columns' not in config:
        raise Exception("Missing 'description_include_columns' in config!")
    includes = config['description_include_columns']
    excludes = set(config.get('description_exclude_columns', [])) if config else set()
    excludes |= SHOPIFY_HEADERS | {None}

    desc = "<p>"
    for col in includes:
        val = row.get(col, None)
        if (
            col not in excludes
            and isinstance(val, (str, float, int, bool, np.generic))
            and pd.notna(val)
            and str(val).strip()
        ):
            label = col.replace('_', ' ')
            desc += f"<strong>{label}: </strong> {val}<br>"
    desc += "</p>"

    # --- BEGIN HARDCODED STERLCO BLOCK ---
    part_number = row.get('Article Number', '')
    voltage = row.get('Voltage', '')
    shipping_weight = row.get('Weight lbs', row.get('Weight', ''))
    boiler_hp = row.get('Boiler HP', '')
    discharge_pressure = row.get('Discharge Pressure PSI', '')
    pump_cap = row.get('Pump Cap (GPM)', '')
    motor_hp = row.get('Motor HP', '')
    rec_cap = row.get('Rec Cap (Gal)', '')

    desc += f"<p><strong>Part Number: {part_number}</strong></p>"
    desc += "<p>Sterlco® atmospherically vented condensate tanks are designed for pumping hot condensate throughout the steam system. The 4300 Series stainless steel unit is designed for wash down duty, sterilization, and corrosive environment applications. Tanks sizes range from 8-714 gallons.</p>"
    desc += "<ul>"
    desc += f"<li>Voltage: {voltage}</li>"
    desc += f"<li>Shipping Weight: {shipping_weight} lb</li>"
    desc += f"<li>Boiler HP: {boiler_hp}</li>"
    desc += f"<li>Discharge Pressure: {discharge_pressure} PSI</li>"
    desc += f"<li>Pump Capacity: {pump_cap} GPM</li>"
    desc += f"<li>Motor HP: {motor_hp}</li>"
    desc += f"<li>Recirculation Capacity: {rec_cap} Gal</li>"
    desc += "<li> The Sterlco® Centrifugal Pumps are capable of pumping hot condensate up to 200° F. These pumps are equipped with heavy-duty cast iron pump housing and bracket, along with a brass impeller to assure long operating life.</li>"
    desc += "<li>Sterl-Seal” ceramic pump seal (250°F)</li>"
    desc += "</ul>"
    desc += "<p><strong>Applications:</strong> Series Condensate Units, commercial HVAC, boiler rooms</p>"
    desc += "<p><a href=\"https://www.sterlcosteam.com/product_category/products/\" target=\"_blank\">Manufacturer Reference</a> | <a href=\"https://www.sterlcosteam.com/wp-content/uploads/2019/01/ts-sterlco-4200-series-boiler-feed-pumps-final.pdf\" target=\"_blank\">Specs Sheet</a></p>"
    desc += "<p><strong>Voltage Selection Guide:</strong></p>"
    desc += "<ul>"
    desc += "<li><strong>1/60/115-208-230</strong> - Single-phase motor for light commercial applications. Compatible with standard building electrical service.</li>"
    desc += "<li><strong>3/60/208-230-460</strong> - Three-phase motor for larger systems or industrial settings. Requires three-phase power supply.</li>"
    desc += "</ul>"
    desc += "<p>Not sure what to choose? Contact our support team for guidance on voltage selection based on your facility.</p>"
    # --- END HARDCODED STERLCO BLOCK ---

    # Only add shipping note if weight > 150
    weight = row.get('Weight', row.get('Weight lbs', 0))
    try:
        w = float(str(weight).replace(',', ''))
    except (ValueError, TypeError):
        w = 0
    if w > 150:
        desc += '<p><em>NOTE: We will contact you during order fulfilment to discuss shipping and handling costs for products weighing more than 150 pounds. These costs will be billed separately.</em></p>'

    context = {k.replace(' ', '_').lower(): v for k, v in row.items() if isinstance(k, str)}
    context.update(row)
    if config:
        context.update({k: v for k, v in config.items()})
    context['description'] = desc

    return safe_eval(seo_formula, context).strip()