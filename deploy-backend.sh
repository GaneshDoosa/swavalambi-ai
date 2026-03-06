#!/bin/bash
#
# Backend Deployment Script
# Deploys backend code changes to AWS Lambda
#
# Usage: ./deploy-backend.sh
#
# Configuration: Set these environment variables or edit deploy-config.sh
#   AWS_PROFILE - AWS CLI profile name
#   AWS_REGION - AWS region
#   LAMBDA_FUNCTION - Lambda function name
#   S3_BUCKET - S3 bucket for deployment packages
#   API_GATEWAY_URL - API Gateway base URL
#

set -e  # Exit on error

# Load configuration from deploy-config.sh if it exists
if [ -f "deploy-config.sh" ]; then
    source deploy-config.sh
fi

# Configuration with defaults (override via environment variables or deploy-config.sh)
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_REGION="${AWS_REGION:-us-east-1}"
LAMBDA_FUNCTION="${LAMBDA_FUNCTION:-swavalambi-api}"
S3_BUCKET="${S3_BUCKET:-your-lambda-bucket}"
API_GATEWAY_URL="${API_GATEWAY_URL:-https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/prod}"
PACKAGE_NAME="deployment-minimal.zip"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Backend Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Validate configuration
if [ "$S3_BUCKET" = "your-lambda-bucket" ]; then
    echo -e "${RED}Error: Please configure deployment settings${NC}"
    echo -e "${YELLOW}Create deploy-config.sh with your AWS settings:${NC}"
    echo -e "  cp deploy-config.example.sh deploy-config.sh"
    echo -e "  # Edit deploy-config.sh with your values"
    exit 1
fi

echo -e "\nConfiguration:"
echo -e "  AWS Profile: $AWS_PROFILE"
echo -e "  AWS Region: $AWS_REGION"
echo -e "  Lambda Function: $LAMBDA_FUNCTION"
echo -e "  S3 Bucket: $S3_BUCKET"

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

cd backend

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Deploying Backend${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}Step 1: Packaging backend code...${NC}"
# Remove old package if exists
rm -f $PACKAGE_NAME

# Clean up old installations
echo -e "${YELLOW}Cleaning up old packages...${NC}"
rm -rf PIL/ Pillow* psycopg2/ psycopg2_binary* pgvector/ pgvector* *.dist-info/ *.libs/ numpy/ numpy*

# Install binary packages directly into backend directory (will be included in zip)
echo -e "${YELLOW}Installing binary packages for Lambda (Linux x86_64)...${NC}"

# Install numpy first (dependency for pgvector)
pip install numpy==1.26.4 -t . \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade \
    --quiet

# Install psycopg2-binary
pip install psycopg2-binary==2.9.9 -t . \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade \
    --quiet

# Install pgvector
pip install pgvector==0.3.6 -t . \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade \
    --quiet

# Install Pillow
pip install Pillow==10.0.0 -t . \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade \
    --quiet

echo -e "${GREEN}✓ Binary packages installed${NC}"

# Verify packages were installed
if [ ! -d "numpy" ]; then
    echo -e "${RED}✗ numpy installation failed${NC}"
    exit 1
fi

if [ ! -d "psycopg2" ]; then
    echo -e "${RED}✗ psycopg2 installation failed${NC}"
    exit 1
fi

if [ ! -d "pgvector" ]; then
    echo -e "${RED}✗ pgvector installation failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Verified: numpy, psycopg2, pgvector, Pillow installed${NC}"

# Create deployment package (code + binary packages)
echo -e "${YELLOW}Creating deployment package...${NC}"
zip -r $PACKAGE_NAME \
  main.py \
  agents/ \
  api/ \
  services/ \
  schemas/ \
  common/ \
  PIL/ \
  Pillow* \
  psycopg2/ \
  psycopg2_binary* \
  pgvector/ \
  pgvector* \
  numpy/ \
  numpy* \
  -x "*.pyc" -x "__pycache__/*" -x "tests/*" -x ".env" -x "*.md" > /dev/null

PACKAGE_SIZE=$(du -h $PACKAGE_NAME | cut -f1)
echo -e "${GREEN}✓ Package created: $PACKAGE_NAME ($PACKAGE_SIZE)${NC}"

echo -e "\n${YELLOW}Step 2: Uploading to S3...${NC}"
aws s3 cp $PACKAGE_NAME s3://$S3_BUCKET/ \
  --profile $AWS_PROFILE \
  --region $AWS_REGION

echo -e "${GREEN}✓ Uploaded to S3${NC}"

echo -e "\n${YELLOW}Step 3: Deploying to Lambda...${NC}"
aws lambda update-function-code \
  --function-name $LAMBDA_FUNCTION \
  --s3-bucket $S3_BUCKET \
  --s3-key $PACKAGE_NAME \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --output json > /dev/null

echo -e "${GREEN}✓ Deployed to Lambda${NC}"

echo -e "\n${YELLOW}Step 4: Waiting for code update to complete...${NC}"
aws lambda wait function-updated \
  --function-name $LAMBDA_FUNCTION \
  --profile $AWS_PROFILE \
  --region $AWS_REGION

echo -e "${GREEN}✓ Code update complete${NC}"

echo -e "\n${YELLOW}Step 5: Updating Lambda configuration...${NC}"
aws lambda update-function-configuration \
  --function-name $LAMBDA_FUNCTION \
  --environment "Variables={
    DYNAMODB_TABLE=swavalambi_users,
    ANTHROPIC_MODEL_ID=claude-sonnet-4-6,
    AI_SECRETS_NAME=swavalambi/ai-credentials,
    COGNITO_CLIENT_ID=2kfmnu9h7rq35jqn45q8jgfj5f,
    COGNITO_USER_POOL_ID=us-east-1_bRKpUL77I,
    USE_LOCAL_CREDENTIALS=false,
    USE_ANTHROPIC=true,
    VECTOR_STORE=pgvector,
    EMBEDDING_PROVIDER=azure-openai
  }" \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --output json > /dev/null

echo -e "${GREEN}✓ Configuration updated${NC}"

echo -e "\n${YELLOW}Step 6: Updating API Gateway CORS...${NC}"
# Get API Gateway ID from the API URL
API_ID=$(echo $API_GATEWAY_URL | sed -n 's|https://\([^.]*\)\.execute-api\..*|\1|p')

if [ -n "$API_ID" ]; then
    aws apigatewayv2 update-api \
      --api-id $API_ID \
      --cors-configuration "AllowOrigins=http://localhost:5173,http://localhost:3000,http://swavalambi-frontend-1772381208.s3-website-us-east-1.amazonaws.com,https://d21tmg809bunv0.cloudfront.net,AllowMethods=GET,POST,PUT,DELETE,OPTIONS,PATCH,AllowHeaders=*,AllowCredentials=true,MaxAge=3600" \
      --profile $AWS_PROFILE \
      --region $AWS_REGION \
      --output json > /dev/null
    
    echo -e "${GREEN}✓ API Gateway CORS updated${NC}"
else
    echo -e "${YELLOW}⚠ Could not extract API Gateway ID - skipping CORS update${NC}"
fi

echo -e "\n${YELLOW}Step 7: Waiting for configuration update...${NC}"
sleep 3

echo -e "\n${YELLOW}Step 8: Testing health endpoint...${NC}"
HEALTH_URL="${API_GATEWAY_URL}/health"
RESPONSE=$(curl -s $HEALTH_URL)

if [[ $RESPONSE == *"ok"* ]]; then
    echo -e "${GREEN}✓ Health check passed: $RESPONSE${NC}"
else
    echo -e "${RED}✗ Health check failed: $RESPONSE${NC}"
    echo -e "${YELLOW}Check logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow --profile $AWS_PROFILE --region $AWS_REGION${NC}"
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Backend deployment complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\nEndpoints:"
echo -e "  Health: ${API_GATEWAY_URL}/health"
echo -e "  API: ${API_GATEWAY_URL}"
echo -e "  Docs: ${API_GATEWAY_URL}/docs"
echo -e "\nView logs:"
echo -e "  aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow --profile $AWS_PROFILE --region $AWS_REGION"
echo ""

cd ..
