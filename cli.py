import os
import sys
import pandas as pd
import time
from processor import process_file

import json

# Load formulas.json if present
formulas = {}
try:
    with open("formulas.json", "r") as f:
        formulas = json.load(f)
        print("✅ Loaded formulas from formulas.json")
except FileNotFoundError:
    print("⚠️ formulas.json not found. Using default formulas.")


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
    print("\n🚀 SHOPIFY IMPORT CLI TOOL v1.0")
    print("=" * 60)

    files = list_files()
    filename = None
    while True:
        choice = input("\nEnter file number to load: ")
        try:
            file_idx = int(choice) - 1
            filename = files[file_idx]
            break
        except (IndexError, ValueError):
            print("Invalid selection. Please enter a valid number from the list.")

    print(f"\n✅ File selected: {filename}")

    # Input with fallbacks
    image_url = input("Enter Image URL for all products: ").strip()
    vendor = input("Vendor name (default: Wilo): ").strip() or "Wilo"
    product_type = input("Product category (default: Booster Pump Systems): ").strip() or "Booster Pump Systems"
    collection = input("Enter Collection (e.g., Helix V, MVI): ").strip() or "General"

    config = {
        "pricing_formula": lambda lp: round(lp * 0.36 * 1.21, 2),
        "cost_formula": lambda lp: round(lp * 0.36, 2),
        "weight_threshold": 150.0,
        "image_url": image_url,
        "vendor": vendor,
        "product_type": product_type,
        "collection": collection,
        "pricing_formula": formulas.get("pricing_formula", "list_price * 0.36 * 1.21"),
        "cost_formula": formulas.get("cost_formula", "list_price * 0.36"),
        "grams_formula": formulas.get("grams_formula", "weight * 453.592")
    }

    # Confirm settings before continuing
    print("\nConfiguration Summary:")
    for k, v in config.items():
        if not callable(v):
            print(f"  {k}: {v}")
    print(f"  File: {filename}")
    proceed = input("Proceed with processing? [Y/n]: ").strip().lower()
    if proceed == 'n':
        print("❌ Operation cancelled.")
        sys.exit(0)

    output_mode = input("\nChoose export type:\n  1. Full Shopify import (53 columns)\n  2. Description-only update\nSelect [1/2]: ")
    if output_mode not in ['1', '2']:
        print("Invalid selection.")
        sys.exit(1)

    mode = 'full' if output_mode == '1' else 'description-only'

    print("\nProcessing file...")
    start = time.time()
    try:
        output_path = process_file(filename, config, mode)
        print(f"\n✅ Export complete: {output_path}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

    print(f"⏱️ Time taken: {round(time.time() - start, 2)}s")

if __name__ == "__main__":
    main()
