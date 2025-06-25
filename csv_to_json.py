import csv
import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import re
class CSVToJSONConverter:
    def __init__(self):
        self.supported_delimiters = [',', ';', '\t', '|', ':']
        self.stats = {
            'rows_processed': 0,
            'rows_skipped': 0,
            'conversion_time': 0
        }
    def detect_delimiter(self, file_path, sample_lines=5):
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as file:
                sample_data = []
                for i, line in enumerate(file):
                    if i >= sample_lines:
                        break
                    sample_data.append(line.strip())
                if not sample_data:
                    return ','
                sniffer = csv.Sniffer()
                sample_text = '\n'.join(sample_data)
                try:
                    dialect = sniffer.sniff(sample_text, delimiters=',;\t|:')
                    return dialect.delimiter
                except csv.Error:
                    delimiter_counts = {}
                    for delimiter in self.supported_delimiters:
                        count = sum(line.count(delimiter) for line in sample_data)
                        delimiter_counts[delimiter] = count
                    best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
                    return best_delimiter if delimiter_counts[best_delimiter] > 0 else ','
        except Exception as e:
            print(f"Warning: Could not detect delimiter ({e}). Using comma as default.")
            return ','
    def clean_field_name(self, field_name):
        if not field_name:
            return "unnamed_field"
        cleaned = field_name.strip()
        cleaned = re.sub(r'[^\w\s-]', '_', cleaned)
        cleaned = re.sub(r'[-\s]+', '_', cleaned)
        cleaned = cleaned.strip('_')
        if cleaned and cleaned[0].isdigit():
            cleaned = f"field_{cleaned}"
        return cleaned.lower() if cleaned else "unnamed_field"
    def detect_data_type(self, value):
        if not value or value.strip() == '':
            return None
        value = value.strip()
        if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
            if value.lower() in ['true', 'yes']:
                return True
            elif value.lower() in ['false', 'no']:
                return False
            elif value == '1':
                return True
            elif value == '0':
                return False
        try:
            if '.' not in value and 'e' not in value.lower():
                return int(value)
            else:
                return float(value)
        except ValueError:
            pass
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  
            r'\d{2}/\d{2}/\d{4}',  
            r'\d{2}-\d{2}-\d{4}',  
        ]
        for pattern in date_patterns:
            if re.match(pattern, value):
                return value  
        return value
    def convert_csv_to_json(self, input_file, output_file=None, **options):
        start_time = datetime.now()
        delimiter = options.get('delimiter', None)
        encoding = options.get('encoding', 'utf-8')
        skip_empty_rows = options.get('skip_empty_rows', True)
        convert_types = options.get('convert_types', True)
        clean_headers = options.get('clean_headers', True)
        output_format = options.get('output_format', 'records')  
        indent = options.get('indent', 2)
        start_row = options.get('start_row', 0)
        max_rows = options.get('max_rows', None)
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file '{input_file}' not found")
        if not delimiter:
            delimiter = self.detect_delimiter(input_file)
            print(f"Auto-detected delimiter: '{delimiter}'")
        if not output_file:
            input_path = Path(input_file)
            output_file = input_path.with_suffix('.json')
        print(f"Converting: {input_file} -> {output_file}")
        print(f"Options: delimiter='{delimiter}', encoding='{encoding}', format='{output_format}'")
        try:
            with open(input_file, 'r', encoding=encoding, newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=delimiter)
                for _ in range(start_row):
                    next(reader, None)
                try:
                    headers = next(reader)
                    if clean_headers:
                        headers = [self.clean_field_name(header) for header in headers]
                except StopIteration:
                    raise ValueError("CSV file appears to be empty or has no header row")
                data = []
                row_count = 0
                for row_num, row in enumerate(reader, start=start_row + 2):  
                    if max_rows and len(data) >= max_rows:
                        break
                    if skip_empty_rows and not any(cell.strip() for cell in row):
                        self.stats['rows_skipped'] += 1
                        continue
                    while len(row) < len(headers):
                        row.append('')
                    if len(row) > len(headers):
                        row = row[:len(headers)]
                    row_dict = {}
                    for i, (header, cell) in enumerate(zip(headers, row)):
                        if convert_types:
                            row_dict[header] = self.detect_data_type(cell)
                        else:
                            row_dict[header] = cell.strip() if cell else ''
                    data.append(row_dict)
                    row_count += 1
                    if row_count % 1000 == 0:
                        print(f"Processed {row_count} rows...", end='\r')
                self.stats['rows_processed'] = row_count
                print(f"\nProcessed {row_count} rows successfully")
                if output_format == 'records':
                    json_data = data
                elif output_format == 'values':
                    json_data = [list(row.values()) for row in data]
                elif output_format == 'index':
                    json_data = {i: row for i, row in enumerate(data)}
                elif output_format == 'columns':
                    json_data = {header: [row[header] for row in data] for header in headers}
                else:
                    raise ValueError(f"Unsupported output format: {output_format}")
                with open(output_file, 'w', encoding='utf-8') as jsonfile:
                    json.dump(json_data, jsonfile, indent=indent, ensure_ascii=False, default=str)
                end_time = datetime.now()
                self.stats['conversion_time'] = (end_time - start_time).total_seconds()
                print(f"\nConversion completed successfully!")
                print(f"Output file: {output_file}")
                print(f"Rows processed: {self.stats['rows_processed']}")
                print(f"Rows skipped: {self.stats['rows_skipped']}")
                print(f"Conversion time: {self.stats['conversion_time']:.2f} seconds")
                print(f"Output file size: {self.format_file_size(os.path.getsize(output_file))}")
                return True
        except Exception as e:
            print(f"Error during conversion: {e}")
            return False
    def format_file_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    def preview_csv(self, input_file, lines=5):
        try:
            delimiter = self.detect_delimiter(input_file)
            print(f"\nPreviewing {input_file}:")
            print(f"Detected delimiter: '{delimiter}'")
            print("-" * 60)
            with open(input_file, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.reader(csvfile, delimiter=delimiter)
                for i, row in enumerate(reader):
                    if i >= lines:
                        break
                    row_preview = [cell[:20] + "..." if len(cell) > 20 else cell for cell in row]
                    print(f"Row {i+1}: {row_preview}")
                if i == 0:
                    print("Headers detected:", len(row))
            print("-" * 60)
        except Exception as e:
            print(f"Error previewing file: {e}")
    def batch_convert(self, input_pattern, output_dir=None):
        from glob import glob
        csv_files = glob(input_pattern)
        if not csv_files:
            print(f"No CSV files found matching pattern: {input_pattern}")
            return
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        successful = 0
        failed = 0
        print(f"Found {len(csv_files)} CSV files to convert")
        for csv_file in csv_files:
            try:
                if output_dir:
                    output_file = os.path.join(output_dir, Path(csv_file).stem + '.json')
                else:
                    output_file = Path(csv_file).with_suffix('.json')
                print(f"\nConverting: {csv_file}")
                if self.convert_csv_to_json(csv_file, str(output_file)):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Failed to convert {csv_file}: {e}")
                failed += 1
        print(f"\nBatch conversion complete:")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
def main():
    parser = argparse.ArgumentParser(
        description="Convert CSV files to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=
    )
    parser.add_argument('input_file', help='Input CSV file path or pattern for batch mode')
    parser.add_argument('output_file', nargs='?', help='Output JSON file path (optional)')
    parser.add_argument('-d', '--delimiter', help='CSV delimiter (auto-detected if not specified)')
    parser.add_argument('-e', '--encoding', default='utf-8', help='File encoding (default: utf-8)')
    parser.add_argument('-f', '--format', choices=['records', 'values', 'index', 'columns'], 
                       default='records', help='Output format (default: records)')
    parser.add_argument('--indent', type=int, default=2, help='JSON indentation (default: 2)')
    parser.add_argument('--no-type-conversion', action='store_true', 
                       help='Disable automatic type conversion')
    parser.add_argument('--no-clean-headers', action='store_true',
                       help='Don\'t clean header names')
    parser.add_argument('--include-empty-rows', action='store_true',
                       help='Include empty rows in output')
    parser.add_argument('--start-row', type=int, default=0,
                       help='Row number to start reading from (0-based)')
    parser.add_argument('--max-rows', type=int,
                       help='Maximum number of rows to convert')
    parser.add_argument('--preview', action='store_true',
                       help='Preview CSV structure without converting')
    parser.add_argument('--batch', action='store_true',
                       help='Batch convert multiple files (use wildcards in input)')
    parser.add_argument('--output-dir', help='Output directory for batch conversion')
    args = parser.parse_args()
    converter = CSVToJSONConverter()
    if args.preview:
        converter.preview_csv(args.input_file)
        return
    if args.batch:
        converter.batch_convert(args.input_file, args.output_dir)
        return
    conversion_options = {
        'delimiter': args.delimiter,
        'encoding': args.encoding,
        'skip_empty_rows': not args.include_empty_rows,
        'convert_types': not args.no_type_conversion,
        'clean_headers': not args.no_clean_headers,
        'output_format': args.format,
        'indent': args.indent,
        'start_row': args.start_row,
        'max_rows': args.max_rows
    }
    try:
        success = converter.convert_csv_to_json(
            args.input_file, 
            args.output_file, 
            **conversion_options
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Conversion failed: {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()
