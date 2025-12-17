#!/usr/bin/env python3
"""Generate test data for CICC project."""

import os
import random

# Configuration
DATA_DIR = "data"
NUM_INPUT_FILES = 10
FILE_SIZE_MB = 2
FILE_SIZE_BYTES = FILE_SIZE_MB * 1024 * 1024
KERNEL_SIZE_BYTES = 1000
NUM_OUTPUT_FILES = 3

def generate_random_bytes(size):
    """Generate random bytes."""
    return bytes(random.getrandbits(8) for _ in range(size))

def xor_bytes(data, kernel):
    """XOR data with kernel (repeating kernel as needed)."""
    result = bytearray(len(data))
    kernel_len = len(kernel)
    for i in range(len(data)):
        result[i] = data[i] ^ kernel[i % kernel_len]
    return bytes(result)

def main():
    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Generate kernel
    print(f"Generating kernel ({KERNEL_SIZE_BYTES} bytes)...")
    kernel = generate_random_bytes(KERNEL_SIZE_BYTES)
    kernel_path = os.path.join(DATA_DIR, "kernel.dat")
    with open(kernel_path, "wb") as f:
        f.write(kernel)
    print(f"  Created {kernel_path}")
    
    # Generate input files
    print(f"\nGenerating {NUM_INPUT_FILES} input files ({FILE_SIZE_MB}MB each)...")
    for i in range(NUM_INPUT_FILES):
        filename = f"in{i}.dat"
        filepath = os.path.join(DATA_DIR, filename)
        data = generate_random_bytes(FILE_SIZE_BYTES)
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"  Created {filepath}")
    
    # Generate output files (first 3 inputs XOR kernel)
    print(f"\nGenerating {NUM_OUTPUT_FILES} output files...")
    for i in range(NUM_OUTPUT_FILES):
        input_file = os.path.join(DATA_DIR, f"in{i}.dat")
        output_file = os.path.join(DATA_DIR, f"out{i}.dat")
        
        with open(input_file, "rb") as f:
            input_data = f.read()
        
        output_data = xor_bytes(input_data, kernel)
        
        with open(output_file, "wb") as f:
            f.write(output_data)
        print(f"  Created {output_file}")
    
    # Create tasklist.txt (files 0-9 need processing)
    tasklist_path = os.path.join(DATA_DIR, "tasklist.txt")
    with open(tasklist_path, "w") as f:
        for i in range(NUM_INPUT_FILES):
            f.write(f"in{i}.dat\n")
    print(f"\nCreated {tasklist_path}")
    
    # Create empty completed.txt
    completed_path = os.path.join(DATA_DIR, "completed.txt")
    with open(completed_path, "w") as f:
        pass
    print(f"Created {completed_path}")
    
    print("\nData generation complete!")
    print(f"Total files created: {NUM_INPUT_FILES} inputs + {NUM_OUTPUT_FILES} outputs + kernel + tasklist + completed")

if __name__ == "__main__":
    main()
