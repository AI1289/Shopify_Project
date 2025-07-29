import os
import json
import sys
import traceback
import time
import pandas as pd

# Import modern processors
from processor import process_file as process_physical
from processor_no_weight import process_file as process_digital

def load_formulas():
    try:
        with open('formulas.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading formulas.json: {e}")
        sys.exit(1)

def main():
    print("==== Shopify CLI Importer ====")
    print("Welcome! This tool will help you convert your supplier spreadsheet into a Shopify-ready CSV.\n")

    # 1. Choose product type
    print("Select import mode:")
    print(" 1. Physical products (with weight, shipping logic)")
    print(" 2. Digital products (no weight/shipping)")
    while True:
        mode_input = input("Enter 1 for physical or 2 for digital: ").strip()
        if mode_input in ['1', '2']:
            break
        print("Invalid selection. Please enter 1 or 2.")
    is_physical = (mode_input == '1')

    # 2. Select input file
    files = [f for f in os.listdir('.') if f.lower().endswith(('.csv', '.xls', '.xlsx')) and not f.startswith('~$')]
    if not files:
        print("No CSV/XLSX files found in current directory.")
        sys.exit(1)
    print("\nAvailable files:")
    for idx, fname in enumerate(files, 1):
        print(f"{idx}: {fname}")
    while True:
        try:
            file_choice = int(input("Enter file number: ").strip())
            if 1 <= file_choice <= len(files):
                break
            print(f"Enter a number between 1 and {len(files)}")
        except ValueError:
            print("Please enter a valid integer.")
    in_file = files[file_choice - 1]
    print(f"Selected: {in_file}")

    # 3. Gather metadata from user
    vendor = input("Vendor name: ").strip()
    product_type = input("Product type: ").strip()
    collection = input("Collection/Tag: ").strip()
    image_url = input("Default image URL (can be blank): ").strip()
    product_category = input("Product category (optional): ").strip()

    # 4. Load formulas/config
    config = load_formulas()
    config['vendor'] = vendor
    config['product_type'] = product_type
    config['collection'] = collection
    config['image_url'] = image_url
    if product_category:
        config['product_category'] = product_category

    # 5. Show config summary
    print("\n=== Config Summary ===")
    for k, v in config.items():
        print(f"{k}: {v}")

    # 6. Export mode
    print("\nExport options:")
    print(" 1. Full Shopify CSV (all fields)")
    print(" 2. Description-only (Handle + HTML body)")
    while True:
        export_choice = input("Enter 1 or 2: ").strip()
        if export_choice in ['1', '2']:
            break
        print("Invalid. Please enter 1 or 2.")
    export_mode = 'full' if export_choice == '1' else 'description-only'

    # 7. Process file
    print(f"\nProcessing file with {'physical' if is_physical else 'digital'} product logic...")
    try:
        if is_physical:
            out_file = process_physical(in_file, config, export_mode)
        else:
            out_file = process_digital(in_file, config, export_mode)
        print(f"\n✅ Export complete: {out_file}\n")
    except Exception as e:
        print("\n❌ Error during processing!")
        traceback.print_exc()
        sys.exit(1)

    print("Thank you for using Shopify CLI Importer.")
    time.sleep(1)

if __name__ == "__main__":
    main()
