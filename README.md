# Shopify Import CLI Tool

A command-line tool to convert supplier Excel/CSV product files into Shopify-ready 53-column CSVs.

## Features
- Accepts `.csv`, `.xls`, `.xlsx`
- Fuzzy column matching
- Price = List × 0.36 × 1.21
- Supports full import or description-only updates
- Adds shipping disclaimers for items >150 lbs
- Logs validation errors to timestamped log file

## Install
```
pip install -r requirements.txt
```

## Run
```
python cli.py
```

## Output
- Exports to `/exports`
- Logs errors to `/exports/errors_<timestamp>.log`

## Branch 2 (processor_no_weight.py)
- Weight is being Set to 0 and Removed from Body and Requires Shipping is False to make it into a Digital Product
