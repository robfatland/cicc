#!/usr/bin/env python3
"""Process data file: XOR with kernel."""

import sys
import os
from datetime import datetime
import boto3
from io import BytesIO

def xor_bytes(data, kernel):
    """XOR data with kernel (repeating kernel as needed)."""
    result = bytearray(len(data))
    kernel_len = len(kernel)
    for i in range(len(data)):
        result[i] = data[i] ^ kernel[i % kernel_len]
    return bytes(result)

def s3_object_exists(s3_client, bucket, key):
    """Check if S3 object exists."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except:
        return False

def find_available_task(s3_client, bucket):
    """Find first available task from tasklist that's not completed and not locked."""
    # Read tasklist from S3
    response = s3_client.get_object(Bucket=bucket, Key="tasklist.txt")
    tasklist = [line.strip() for line in response['Body'].read().decode('utf-8').split('\n') if line.strip()]
    
    # Read completed from S3
    completed = set()
    if s3_object_exists(s3_client, bucket, "completed.txt"):
        response = s3_client.get_object(Bucket=bucket, Key="completed.txt")
        completed = set(line.strip() for line in response['Body'].read().decode('utf-8').split('\n') if line.strip())
    
    # Find available task
    for filename in tasklist:
        # Check if already completed
        if filename in completed:
            continue
        
        # Extract file number (in3.dat -> 3)
        file_num = filename.replace("in", "").replace(".dat", "")
        semaphore = f"semaphore{file_num}.txt"
        
        # Check if semaphore exists in S3
        if s3_object_exists(s3_client, bucket, semaphore):
            continue
        
        # Found available task
        return filename, file_num
    
    return None, None

def main():
    # Get bucket name from environment variable
    bucket = os.environ.get('S3_BUCKET', 'cicc-12132025')
    
    # Initialize S3 client (uses IAM role credentials automatically)
    s3_client = boto3.client('s3')
    
    semaphore_key = None
    file_num = None
    
    try:
        # Find available task
        input_filename, file_num = find_available_task(s3_client, bucket)
        
        if input_filename is None:
            print("No available tasks found")
            sys.exit(1)
        
        print(f"Found available task: {input_filename}")
        
        # Create semaphore in S3 (zero-length file)
        semaphore_key = f"semaphore{file_num}.txt"
        s3_client.put_object(Bucket=bucket, Key=semaphore_key, Body=b'')
        print(f"Created semaphore: {semaphore_key}")
        
        # File keys
        output_filename = input_filename.replace("in", "out")
        
        print(f"Processing {input_filename}...")
        
        # Read kernel from S3
        response = s3_client.get_object(Bucket=bucket, Key="kernel.dat")
        kernel = response['Body'].read()
        
        # Read input data from S3
        response = s3_client.get_object(Bucket=bucket, Key=input_filename)
        input_data = response['Body'].read()
        
        # XOR operation
        output_data = xor_bytes(input_data, kernel)
        
        # Write output to S3
        s3_client.put_object(Bucket=bucket, Key=output_filename, Body=output_data)
        print(f"Created {output_filename}")
        
        # Update completed.txt in S3
        completed_content = ""
        if s3_object_exists(s3_client, bucket, "completed.txt"):
            response = s3_client.get_object(Bucket=bucket, Key="completed.txt")
            completed_content = response['Body'].read().decode('utf-8')
        
        completed_content += f"{input_filename}\n"
        s3_client.put_object(Bucket=bucket, Key="completed.txt", Body=completed_content.encode('utf-8'))
        print(f"Added {input_filename} to completed.txt")
        
        # Remove semaphore from S3
        if semaphore_key:
            s3_client.delete_object(Bucket=bucket, Key=semaphore_key)
            print(f"Removed semaphore: {semaphore_key}")
        
        print("SUCCESS")
        
    except Exception as e:
        # Write error file with timestamp to S3
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        error_filename = f"error-{timestamp}.txt"
        
        error_msg = f"process.py was unable to complete a processing task at {timestamp}\n"
        error_msg += f"Error: {str(e)}\n"
        
        try:
            s3_client.put_object(Bucket=bucket, Key=error_filename, Body=error_msg.encode('utf-8'))
            print(f"ERROR: {error_msg}")
            print(f"Error file created: {error_filename}")
        except:
            print(f"ERROR: {error_msg}")
            print("Failed to write error file to S3")
        
        # Clean up semaphore if it exists
        if semaphore_key:
            try:
                s3_client.delete_object(Bucket=bucket, Key=semaphore_key)
                print(f"Cleaned up semaphore: {semaphore_key}")
            except:
                pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
