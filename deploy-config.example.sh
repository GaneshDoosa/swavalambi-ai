#!/bin/bash
#
# Deployment Configuration Template
# Copy this file to deploy-config.sh and fill in your values
#
# Usage:
#   cp deploy-config.example.sh deploy-config.sh
#   # Edit deploy-config.sh with your AWS resource values
#   # deploy-config.sh is gitignored for security
#

# AWS Configuration
export AWS_PROFILE="your-aws-profile"           # e.g., "swavalambi-cli" or "default"
export AWS_REGION="us-east-1"                   # AWS region

# Backend Configuration
export LAMBDA_FUNCTION="your-lambda-function"   # e.g., "swavalambi-api"
export S3_BUCKET="your-lambda-bucket"           # S3 bucket for Lambda deployment packages
export API_GATEWAY_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/prod"

# Frontend Configuration
export S3_BUCKET_FRONTEND="your-frontend-bucket"  # S3 bucket for frontend hosting
export CLOUDFRONT_URL="https://your-cloudfront-id.cloudfront.net"  # Optional: CloudFront URL
export S3_WEBSITE_URL="http://your-frontend-bucket.s3-website-us-east-1.amazonaws.com"

# Example values (replace with your actual values):
# export AWS_PROFILE="swavalambi-cli"
# export AWS_REGION="us-east-1"
# export LAMBDA_FUNCTION="swavalambi-api"
# export S3_BUCKET="swavalambi-lambda-1772374368"
# export API_GATEWAY_URL="https://9r8zwqxb6l.execute-api.us-east-1.amazonaws.com/prod"
# export S3_BUCKET_FRONTEND="swavalambi-frontend-1772381208"
# export CLOUDFRONT_URL="https://d21tmg809bunv0.cloudfront.net"
# export S3_WEBSITE_URL="http://swavalambi-frontend-1772381208.s3-website-us-east-1.amazonaws.com"
