# Quick Deployment Guide

Minimal steps to deploy backend and frontend changes.

---

## Prerequisites

- AWS CLI configured with profile `swavalambi-cli`
- Python 3.12 environment: `conda activate ai4bharat`
- Node.js 18+

---

## Deploy Backend (Code Changes)

```bash
cd backend

# Package code only (no dependencies)
zip -r deployment-minimal.zip \
  main.py agents/ api/ services/ schemas/ \
  -x "*.pyc" -x "__pycache__/*" -x "tests/*" -x ".env"

# Upload to S3
aws s3 cp deployment-minimal.zip s3://swavalambi-lambda-1772374368/ \
  --profile swavalambi-cli --region us-east-1

# Deploy to Lambda
aws lambda update-function-code \
  --function-name swavalambi-api \
  --s3-bucket swavalambi-lambda-1772374368 \
  --s3-key deployment-minimal.zip \
  --profile swavalambi-cli --region us-east-1
```

**Verify:** `curl https://9r8zwqxb6l.execute-api.us-east-1.amazonaws.com/prod/health`

---

## Deploy Frontend (UI Changes)

```bash
cd frontend

# Build production bundle
npm run build

# Deploy to S3
aws s3 sync dist/ s3://swavalambi-frontend-1772381208/ \
  --delete \
  --profile swavalambi-cli --region us-east-1
```

**Verify:** Open `https://d21tmg809bunv0.cloudfront.net` (or S3 URL)

**Note:** CloudFront caching may delay updates (5-10 min). To force refresh:
```bash
aws cloudfront create-invalidation \
  --distribution-id E3VQPW8EXAMPLE \
  --paths "/*" \
  --profile swavalambi-cli
```

---

## Update Lambda Dependencies (Rare)

Only needed if you add new Python packages to `requirements.txt`.

```bash
cd backend

# Rebuild layer
rm -rf lambda-layer
mkdir -p lambda-layer/python
pip install -r requirements.txt \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --target lambda-layer/python \
  --python-version 3.12

# Package and upload
cd lambda-layer
zip -r layer.zip python/
aws s3 cp layer.zip s3://swavalambi-lambda-1772374368/lambda-layer.zip \
  --profile swavalambi-cli --region us-east-1

# Publish new layer version
aws lambda publish-layer-version \
  --layer-name swavalambi-dependencies \
  --description "Python 3.12 dependencies" \
  --content S3Bucket=swavalambi-lambda-1772374368,S3Key=lambda-layer.zip \
  --compatible-runtimes python3.12 \
  --profile swavalambi-cli --region us-east-1

# Update Lambda to use new layer (replace VERSION with output from above)
aws lambda update-function-configuration \
  --function-name swavalambi-api \
  --layers arn:aws:lambda:us-east-1:096668245811:layer:swavalambi-dependencies:VERSION \
  --profile swavalambi-cli --region us-east-1
```

---

## View Logs

```bash
# Lambda logs (backend errors)
aws logs tail /aws/lambda/swavalambi-api \
  --follow \
  --profile swavalambi-cli --region us-east-1
```

---

## Endpoints

- **Frontend (HTTPS):** https://d21tmg809bunv0.cloudfront.net
- **Frontend (HTTP):** http://swavalambi-frontend-1772381208.s3-website-us-east-1.amazonaws.com
- **Backend API:** https://9r8zwqxb6l.execute-api.us-east-1.amazonaws.com/prod
- **Health Check:** https://9r8zwqxb6l.execute-api.us-east-1.amazonaws.com/prod/health

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Backend changes not reflecting | Redeploy backend code (see above) |
| Frontend changes not showing | Clear browser cache or wait 5-10 min for CloudFront |
| 500 errors | Check Lambda logs: `aws logs tail /aws/lambda/swavalambi-api` |
| Import errors | Update Lambda layer with new dependencies |

---

**That's it!** Most deployments only need the first two sections (backend + frontend).
