#!/bin/bash
# Reset S3 bucket to initial state from data folder

echo "Resetting S3 bucket to initial state..."

# Remove all files from s3 folder
rm -f ~/cicc/s3/*

# Copy all files from data folder to s3
cp ~/cicc/data/* ~/cicc/s3/

echo "S3 bucket reset complete"
ls -lh ~/cicc/s3/
