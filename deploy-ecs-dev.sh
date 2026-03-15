#!/bin/bash
# Deploy to dev ECS
set -e

source deploy-config.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Dev ECS Deployment${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}Step 1: Logging in to ECR...${NC}"
aws ecr get-login-password \
  --region $AWS_REGION \
  --profile $AWS_PROFILE | \
  docker login --username AWS --password-stdin \
  $(echo $ECR_REPO | cut -d'/' -f1)
echo -e "${GREEN}✓ ECR login successful${NC}"

echo -e "\n${YELLOW}Step 2: Building Docker image (dev)...${NC}"
docker build -t swavalambi-backend-dev ./backend
echo -e "${GREEN}✓ Image built${NC}"

echo -e "\n${YELLOW}Step 3: Tagging and pushing as :dev...${NC}"
docker tag swavalambi-backend-dev:latest $ECR_REPO:dev
docker push $ECR_REPO:dev
echo -e "${GREEN}✓ Image pushed to ECR with :dev tag${NC}"

echo -e "\n${YELLOW}Step 4: Updating dev ECS service...${NC}"
LATEST_TASK_DEF=$(aws ecs describe-task-definition \
  --task-definition swavalambi-backend-dev \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)
echo "Using task definition: $LATEST_TASK_DEF"

aws ecs update-service \
  --cluster $ECS_CLUSTER \
  --service swavalambi-backend-dev \
  --task-definition $LATEST_TASK_DEF \
  --force-new-deployment \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --output json > /dev/null
echo -e "${GREEN}✓ Dev service update triggered${NC}"

echo -e "\n${YELLOW}Step 5: Waiting for deployment...${NC}"
aws ecs wait services-stable \
  --cluster $ECS_CLUSTER \
  --services swavalambi-backend-dev \
  --profile $AWS_PROFILE \
  --region $AWS_REGION
echo -e "${GREEN}✓ Dev service stable${NC}"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Dev deployment complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\nDev backend: $ECS_ALB_DEV_URL"
echo -e "View logs: aws logs tail /ecs/swavalambi-backend-dev --follow --profile $AWS_PROFILE"
