#!/usr/bin/env python3
"""XOR inversion test: Verify out3.dat XOR kernel.dat equals in3.dat"""

import boto3

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

def main():
    bucket = 'cicc-12132025'
    s3_client = boto3.client('s3')
    
    # Check if out3.dat exists
    if not s3_object_exists(s3_client, bucket, 'out3.dat'):
        print("test file out3.dat not found")
        return
    
    # Check if in3.dat exists
    if not s3_object_exists(s3_client, bucket, 'in3.dat'):
        print("input file in3.dat not found")
        return
    
    # Check if kernel.dat exists
    if not s3_object_exists(s3_client, bucket, 'kernel.dat'):
        print("kernel file kernel.dat not found")
        return
    
    try:
        # Read kernel from S3
        response = s3_client.get_object(Bucket=bucket, Key='kernel.dat')
        kernel = response['Body'].read()
        
        # Read out3.dat from S3
        response = s3_client.get_object(Bucket=bucket, Key='out3.dat')
        out3_data = response['Body'].read()
        
        # Read in3.dat from S3
        response = s3_client.get_object(Bucket=bucket, Key='in3.dat')
        in3_data = response['Body'].read()
        
        # XOR out3.dat with kernel
        xor_result = xor_bytes(out3_data, kernel)
        
        # Compare with in3.dat
        if xor_result == in3_data:
            print("xor inverse test successful")
        else:
            print("xor inverse test fail")
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    main()