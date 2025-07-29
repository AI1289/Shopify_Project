import ast
import pandas as pd

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
    """
    Build HTML Shopify description, top fields first, then any others except excluded ones.
    """
    # Dynamic field selection from config or fallback
    includes = config.get('description_include_columns', ['Model', 'Voltage', 'Power']) if config else ['Model', 'Voltage', 'Power']
    excludes = set(config.get('description_exclude_columns', [])) if config else set()
    excludes |= SHOPIFY_HEADERS | {None}
    includes_set = set(includes)

    # Add included fields at the top (fixed order)
    desc = "<p>"
    for col in includes:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            label = col.replace('_', ' ')
            desc += f"<strong>{label}: </strong> {row[col]}<br>"
    desc += "</p>"

    # Add all other eligible columns as their own block
    for key, value in row.items():
        if (
            key in includes_set or
            key in excludes or
            pd.isna(value) or
            str(value).strip() == ''
        ):
            continue
        desc += f"<p><strong>{key}: </strong> {value}</p>"

    # Optionally: footer/note/link, can be conditional if desired
    desc += '<p><em>NOTE: We will contact you during order fulfilment to discuss shipping and handling costs for products weighing more than 150 pounds. These costs will be billed separately.</em></p>'
    desc += '<p><a href="https://wilo.com/en/overview.html" target="_blank">View Manufacturer Website</a></p>'

    context = {k.replace(' ', '_').lower(): v for k, v in row.items() if isinstance(k, str)}
    context.update(row)
    context['description'] = desc

    return safe_eval(seo_formula, context).strip()
