import os
import sys
import hashlib
import zlib
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
class FileHasher:
    SUPPORTED_ALGORITHMS = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
        'blake2b': hashlib.blake2b,
        'blake2s': hashlib.blake2s
    }
    def __init__(self, chunk_size: int = 65536):
        self.chunk_size = chunk_size
        self.processed_files = 0
        self.total_size = 0
    def calculate_hash(self, filepath: str, algorithm: str = 'sha256') -> Optional[str]:
        if algorithm not in self.SUPPORTED_ALGORITHMS and algorithm != 'crc32':
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        try:
            if algorithm == 'crc32':
                return self._calculate_crc32(filepath)
            else:
                return self._calculate_cryptographic_hash(filepath, algorithm)
        except (IOError, OSError) as e:
            print(f"Error reading file {filepath}: {e}")
            return None
    def _calculate_crc32(self, filepath: str) -> str:
        crc = 0
        with open(filepath, 'rb') as f:
            while chunk := f.read(self.chunk_size):
                crc = zlib.crc32(chunk, crc)
        return f"{crc & 0xffffffff:08x}"
    def _calculate_cryptographic_hash(self, filepath: str, algorithm: str) -> str:
        hash_obj = self.SUPPORTED_ALGORITHMS[algorithm]()
        with open(filepath, 'rb') as f:
            while chunk := f.read(self.chunk_size):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    def calculate_multiple_hashes(self, filepath: str, algorithms: List[str]) -> Dict[str, str]:
        hash_objects = {}
        for algo in algorithms:
            if algo == 'crc32':
                hash_objects[algo] = 0
            elif algo in self.SUPPORTED_ALGORITHMS:
                hash_objects[algo] = self.SUPPORTED_ALGORITHMS[algo]()
            else:
                raise ValueError(f"Unsupported algorithm: {algo}")
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    for algo, hash_obj in hash_objects.items():
                        if algo == 'crc32':
                            hash_objects[algo] = zlib.crc32(chunk, hash_obj)
                        else:
                            hash_obj.update(chunk)
            results = {}
            for algo, hash_obj in hash_objects.items():
                if algo == 'crc32':
                    results[algo] = f"{hash_obj & 0xffffffff:08x}"
                else:
                    results[algo] = hash_obj.hexdigest()
            return results
        except (IOError, OSError) as e:
            print(f"Error reading file {filepath}: {e}")
            return {}
    def hash_file(self, filepath: str, algorithms: List[str] = None) -> Dict:
        if algorithms is None:
            algorithms = ['sha256']
        if not os.path.isfile(filepath):
            return {'error': f"File not found: {filepath}"}
        file_stat = os.stat(filepath)
        file_info = {
            'filepath': os.path.abspath(filepath),
            'filename': os.path.basename(filepath),
            'size': file_stat.st_size,
            'modified': time.ctime(file_stat.st_mtime),
            'modified_timestamp': file_stat.st_mtime,
            'hashes': {},
            'processing_time': 0
        }
        start_time = time.time()
        if len(algorithms) == 1:
            hash_value = self.calculate_hash(filepath, algorithms[0])
            if hash_value:
                file_info['hashes'][algorithms[0]] = hash_value
        else:
            file_info['hashes'] = self.calculate_multiple_hashes(filepath, algorithms)
        file_info['processing_time'] = time.time() - start_time
        self.processed_files += 1
        self.total_size += file_info['size']
        return file_info
    def hash_directory(self, directory: str, algorithms: List[str] = None, 
                      recursive: bool = True, extensions: List[str] = None) -> List[Dict]:
        if algorithms is None:
            algorithms = ['sha256']
        results = []
        if not os.path.isdir(directory):
            print(f"Error: '{directory}' is not a valid directory")
            return results
        print(f"Scanning directory: {directory}")
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if extensions:
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext not in extensions:
                        continue
                filepath = os.path.join(root, filename)
                print(f"Processing: {filename}", end='\r')
                file_info = self.hash_file(filepath, algorithms)
                if 'error' not in file_info:
                    results.append(file_info)
                else:
                    print(f"\n{file_info['error']}")
            if not recursive:
                break
        print(f"\nProcessed {len(results)} files")
        return results
    def verify_hashes(self, hash_file: str, algorithm: str = 'sha256') -> Dict:
        verification_results = {
            'verified': [],
            'failed': [],
            'missing': [],
            'errors': []
        }
        try:
            with open(hash_file, 'r') as f:
                content = f.read().strip()
                if content.startswith('{') or content.startswith('['):
                    hash_data = json.loads(content)
                else:
                    hash_data = self._parse_simple_hash_file(content, algorithm)
        except json.JSONDecodeError:
            with open(hash_file, 'r') as f:
                hash_data = self._parse_simple_hash_file(f.read(), algorithm)
        except Exception as e:
            verification_results['errors'].append(f"Error reading hash file: {e}")
            return verification_results
        if isinstance(hash_data, list):
            files_to_verify = hash_data
        else:
            files_to_verify = [hash_data]
        for file_entry in files_to_verify:
            if isinstance(file_entry, dict):
                filepath = file_entry.get('filepath')
                expected_hashes = file_entry.get('hashes', {})
            else:
                filepath = file_entry.get('filepath')
                expected_hashes = {algorithm: file_entry.get('hash')}
            if not os.path.exists(filepath):
                verification_results['missing'].append({
                    'filepath': filepath,
                    'reason': 'File not found'
                })
                continue
            print(f"Verifying: {os.path.basename(filepath)}", end='\r')
            algorithms_to_check = list(expected_hashes.keys())
            current_file_info = self.hash_file(filepath, algorithms_to_check)
            if 'error' in current_file_info:
                verification_results['errors'].append({
                    'filepath': filepath,
                    'error': current_file_info['error']
                })
                continue
            verification_result = {
                'filepath': filepath,
                'filename': current_file_info['filename'],
                'size': current_file_info['size'],
                'hash_matches': {},
                'overall_match': True
            }
            for algo, expected_hash in expected_hashes.items():
                current_hash = current_file_info['hashes'].get(algo)
                matches = current_hash and current_hash.lower() == expected_hash.lower()
                verification_result['hash_matches'][algo] = {
                    'expected': expected_hash,
                    'current': current_hash,
                    'matches': matches
                }
                if not matches:
                    verification_result['overall_match'] = False
            if verification_result['overall_match']:
                verification_results['verified'].append(verification_result)
            else:
                verification_results['failed'].append(verification_result)
        print(f"\nVerification complete.")
        return verification_results
    def _parse_simple_hash_file(self, content: str, default_algorithm: str) -> List[Dict]:
        results = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                hash_value, filepath = parts
                if filepath.startswith('*'):
                    filepath = filepath[1:]
                results.append({
                    'filepath': filepath,
                    'hash': hash_value
                })
        return results
    def save_hashes(self, hash_results: List[Dict], output_file: str, 
                   format_type: str = 'json') -> bool:
        try:
            with open(output_file, 'w') as f:
                if format_type == 'json':
                    json.dump(hash_results, f, indent=2)
                elif format_type == 'simple':
                    for result in hash_results:
                        if result.get('hashes'):
                            algo = list(result['hashes'].keys())[0]
                            hash_value = result['hashes'][algo]
                            f.write(f"{hash_value}  {result['filepath']}\n")
                elif format_type == 'detailed':
                    self._save_detailed_format(f, hash_results)
            print(f"Hash results saved to: {output_file}")
            return True
        except Exception as e:
            print(f"Error saving hash results: {e}")
            return False
    def _save_detailed_format(self, file_handle, hash_results: List[Dict]):
        file_handle.write("FILE HASH REPORT\n")
        file_handle.write("=" * 50 + "\n")
        file_handle.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_handle.write(f"Total files: {len(hash_results)}\n\n")
        for i, result in enumerate(hash_results, 1):
            file_handle.write(f"File {i}: {result['filename']}\n")
            file_handle.write(f"Path: {result['filepath']}\n")
            file_handle.write(f"Size: {self.format_size(result['size'])}\n")
            file_handle.write(f"Modified: {result['modified']}\n")
            file_handle.write("Hashes:\n")
            for algo, hash_value in result['hashes'].items():
                file_handle.write(f"  {algo.upper()}: {hash_value}\n")
            file_handle.write(f"Processing time: {result['processing_time']:.3f}s\n")
            file_handle.write("\n" + "-" * 40 + "\n\n")
    def format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    def print_results(self, results: List[Dict], show_details: bool = False):
        if not results:
            print("No files processed.")
            return
        print(f"\nHash Results ({len(results)} files):")
        print("=" * 60)
        for result in results:
            print(f"\nFile: {result['filename']}")
            if show_details:
                print(f"Path: {result['filepath']}")
                print(f"Size: {self.format_size(result['size'])}")
                print(f"Modified: {result['modified']}")
            print("Hashes:")
            for algo, hash_value in result['hashes'].items():
                print(f"  {algo.upper()}: {hash_value}")
            if show_details:
                print(f"Processing time: {result['processing_time']:.3f}s")
    def print_verification_results(self, results: Dict):
        print(f"\nVerification Results:")
        print("=" * 50)
        print(f"Verified: {len(results['verified'])}")
        print(f"Failed: {len(results['failed'])}")
        print(f"Missing: {len(results['missing'])}")
        print(f"Errors: {len(results['errors'])}")
        if results['failed']:
            print(f"\nFAILED VERIFICATIONS:")
            for failure in results['failed']:
                print(f"  ❌ {failure['filename']}")
                for algo, match_info in failure['hash_matches'].items():
                    if not match_info['matches']:
                        print(f"     {algo.upper()}: Expected {match_info['expected']}")
                        print(f"     {algo.upper()}: Got      {match_info['current']}")
        if results['missing']:
            print(f"\nMISSING FILES:")
            for missing in results['missing']:
                print(f"  ❓ {missing['filepath']}")
        if results['errors']:
            print(f"\nERRORS:")
            for error in results['errors']:
                print(f"  ⚠️  {error}")
def main():
    parser = argparse.ArgumentParser(description="Generate and verify file hashes")
    parser.add_argument("path", help="File or directory path")
    parser.add_argument("-a", "--algorithm", choices=list(FileHasher.SUPPORTED_ALGORITHMS.keys()) + ['crc32'],
                       default="sha256", help="Hash algorithm to use")
    parser.add_argument("-m", "--multiple", nargs="+", 
                       choices=list(FileHasher.SUPPORTED_ALGORITHMS.keys()) + ['crc32'],
                       help="Calculate multiple hashes")
    parser.add_argument("-r", "--recursive", action="store_true",
                       help="Process directories recursively")
    parser.add_argument("-e", "--extensions", nargs="*",
                       help="File extensions to include")
    parser.add_argument("-o", "--output", help="Output file for hash results")
    parser.add_argument("-f", "--format", choices=['json', 'simple', 'detailed'],
                       default='json', help="Output format")
    parser.add_argument("-v", "--verify", help="Verify against hash file")
    parser.add_argument("--chunk-size", type=int, default=65536,
                       help="Chunk size for reading files (bytes)")
    parser.add_argument("--details", action="store_true",
                       help="Show detailed information")
    args = parser.parse_args()
    hasher = FileHasher(chunk_size=args.chunk_size)
    if args.multiple:
        algorithms = args.multiple
    else:
        algorithms = [args.algorithm]
    extensions = None
    if args.extensions:
        extensions = [ext if ext.startswith('.') else '.' + ext 
                     for ext in args.extensions]
        extensions = [ext.lower() for ext in extensions]
    if args.verify:
        results = hasher.verify_hashes(args.verify, args.algorithm)
        hasher.print_verification_results(results)
        return
    start_time = time.time()
    if os.path.isfile(args.path):
        result = hasher.hash_file(args.path, algorithms)
        if 'error' not in result:
            results = [result]
        else:
            print(result['error'])
            return
    elif os.path.isdir(args.path):
        results = hasher.hash_directory(args.path, algorithms, args.recursive, extensions)
    else:
        print(f"Error: '{args.path}' is not a valid file or directory")
        return
    total_time = time.time() - start_time
    hasher.print_results(results, args.details)
    print(f"\nSummary:")
    print(f"Files processed: {len(results)}")
    print(f"Total size: {hasher.format_size(hasher.total_size)}")
    print(f"Total time: {total_time:.2f}s")
    if total_time > 0:
        print(f"Throughput: {hasher.format_size(hasher.total_size / total_time)}/s")
    if args.output:
        hasher.save_hashes(results, args.output, args.format)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
