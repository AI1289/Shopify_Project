import os
import sys
import importlib
import pandas as pd
import time
import json

# --- Processor Selection ---
def select_processor():
    """
    Prompt user to choose which processor module to use.
    """
    print("Choose processor version:")
    print("  1) Standard (processor.py)")
    print("  2) No-weight (processor_no_weight.py)")
    choice = input("Enter 1 or 2: ").strip()
    return 'processor_no_weight' if choice == '2' else 'processor'

# Load formulas.json if present
formulas = {}
try:
    with open("formulas.json", "r") as f:
        formulas = json.load(f)
        print("✅ Loaded formulas from formulas.json")
except FileNotFoundError:
    print("⚠️ formulas.json not found. Using default formulas.")

# Choose processor module
module_name = select_processor()
try:
    processor_mod = importlib.import_module(module_name)
except ImportError:
    print(f"Error: could not import '{module_name}'. Make sure the file exists.")
    sys.exit(1)

# Get the process_file function from the chosen module
process_file = getattr(processor_mod, 'process_file', None)
if process_file is None:
    print(f"Error: 'process_file' not found in module '{module_name}'.")
    sys.exit(1)

# CLI Main Flow

def list_files():
    files = [f for f in os.listdir('.') if f.endswith(('.csv', '.xls', '.xlsx'))]
    if not files:
        print("No input files found.")
        sys.exit(1)
    print("\nAvailable files:")
    for i, file in enumerate(files):
        print(f"  {i + 1}. {file}")
    return files


def main():
    print("\n🚀 SHOPIFY IMPORT CLI TOOL v2")
    print("=" * 60)

    files = list_files()
    while True:
        choice = input("\nEnter file number to load: ")
        try:
            file_idx = int(choice) - 1
            filename = files[file_idx]
            break
        except (IndexError, ValueError):
            print("Invalid selection. Please enter a valid number.")
    print(f"\n✅ File selected: {filename}")

    # Gathering other inputs
    image_url = input("Enter Image URL for all products: ").strip()
    vendor = input("Vendor name (default: Wilo): ").strip() or "Wilo"
    product_type = input("Product Type (default: Booster Pump Systems): ").strip() or "Booster Pump Systems"
    collection = input("Enter Collection (e.g., Helix V, MVI): ").strip() or "General"

    config = {
        "pricing_formula": formulas.get("pricing_formula", "round(list_price * 0.36 * 1.15, 2)"),
        "cost_formula": formulas.get("cost_formula", "round(list_price * 0.36, 2)"),
        "grams_formula": formulas.get("grams_formula", "round(weight * 453.592)"),
        "vendor_formula": formulas.get("vendor_formula", "'{vendor}'"),
        "product_type_formula": formulas.get("product_type_formula", "'{product_type}'"),
        "seo_title_formula": formulas.get(
            "seo_title_formula",
            "f'{collection} {model} – {vendor} {collection} Series {voltage}'"
        ),
        "seo_description_formula": formulas.get(
            "seo_description_formula",
            "f'{collection} {model} {description} {price} USD\nBuy {model} online. Durable, efficient booster pump system from {vendor}.'"
        ),
        "weight_threshold": 150.0,
        "image_url": image_url,
        "vendor": vendor,
        "product_type": product_type,
        "collection": collection
    }

    # Show config summary
    print("\nConfiguration Summary:")
    for k, v in config.items():
        if not callable(v):
            print(f"  {k}: {v}")
    print(f"  File: {filename}")

    proceed = input("Proceed with processing? [Y/n]: ").strip().lower()
    if proceed == 'n':
        print("❌ Operation cancelled.")
        sys.exit(0)

    mode_choice = input(
        "\nChoose export type:\n  1. Full Shopify import (53 columns)\n  2. Description-only update\nSelect [1/2]: "
    )
    if mode_choice not in ['1', '2']:
        print("Invalid selection.")
        sys.exit(1)
    mode = 'full' if mode_choice == '1' else 'description-only'

    # Process and export
    print("\nProcessing file...")
    start = time.time()
    try:
        output_path = process_file(filename, config, mode)
        print(f"\n✅ Export complete: {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    print(f"⏱️ Time taken: {round(time.time() - start, 2)}s")


if __name__ == "__main__":
    main()
