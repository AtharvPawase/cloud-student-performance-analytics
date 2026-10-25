#!/usr/bin/env bash
# Deploy the Student Performance Analytics dashboard with a Cognito admin account.
# You can either set ADMIN_EMAIL/ADMIN_PASSWORD before running, or enter them when prompted.
# Usage: ./deploy.sh
#        ./deploy.sh destroy
set -euo pipefail
cd "$(dirname "$0")"

STACK=${STACK:-student-analytics-dev}
REGION=${AWS_REGION:-$(aws configure get region)}
export AWS_DEFAULT_REGION="$REGION"

out() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

if [ "${1:-}" = "destroy" ]; then
  aws s3 rm "s3://$(out DataBucketName)" --recursive
  aws s3 rm "s3://$(out DashboardBucketName)" --recursive
  aws cloudformation delete-stack --stack-name "$STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$STACK"
  echo "Stack $STACK deleted."
  exit 0
fi

if [ -z "${ADMIN_EMAIL:-}" ]; then
  read -r -p "Admin email: " ADMIN_EMAIL
fi

if [ -z "${ADMIN_PASSWORD:-}" ]; then
  read -r -s -p "Admin password (8+ chars, upper/lower/number): " ADMIN_PASSWORD
  echo
fi

if [ -z "$ADMIN_EMAIL" ]; then
  echo "Admin email cannot be empty." >&2
  exit 1
fi
if [ -z "$ADMIN_PASSWORD" ]; then
  echo "Admin password cannot be empty." >&2
  exit 1
fi

python3 build_template.py
aws cloudformation validate-template \
  --template-body file://cloudformation/template.yaml > /dev/null

aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file cloudformation/template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides AdminEmail="$ADMIN_EMAIL" \
  --tags Project=student-performance-analytics Environment=dev Owner=student Purpose=analytics-dashboard

USER_POOL_ID="$(out UserPoolId)"
CLIENT_ID="$(out UserPoolClientId)"
API_URL="$(out HttpApiUrl)"
WS_URL="$(out WebSocketUrl)"
DASHBOARD_URL="$(out DashboardUrl)"

aws cognito-idp admin-set-user-password \
  --user-pool-id "$USER_POOL_ID" \
  --username "$ADMIN_EMAIL" \
  --password "$ADMIN_PASSWORD" \
  --permanent

cat > dashboard/config.js <<CFG
window.APP_CONFIG={region:"$REGION",apiUrl:"$API_URL",wsUrl:"$WS_URL",clientId:"$CLIENT_ID"};
CFG

aws s3 cp data/sample_student_data.csv \
  "s3://$(out DataBucketName)/raw/sample_student_data.csv"

aws s3 sync dashboard "s3://$(out DashboardBucketName)" --delete

echo
echo "Deployment complete."
echo "Dashboard: $DASHBOARD_URL"
echo "Admin login: $ADMIN_EMAIL"
echo "Password: the password you entered during deployment."
