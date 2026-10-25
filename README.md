# Real-Time Cloud-Based Student Performance Analytics Dashboard

AWS implementation of the project synopsis. **All infrastructure is one CloudFormation template** (`cloudformation/template.yaml`, generated from `template.base.yaml` + `lambda/*.py` by `build_template.py`).

Flow: CSV in S3 `raw/` (or `POST /records`) -> DynamoDB -> DynamoDB Stream -> Lambda updates summary + pushes to WebSocket -> dashboard redraws. Cognito signs users in; groups `teacher`, `hod`, `admin` control writes.

| Synopsis component | AWS service |
|---|---|
| Web app / dashboard | S3 static website (`dashboard/`, your design + Chart.js) |
| API service | API Gateway HTTP API + Lambda, protected by a Cognito JWT authorizer |
| Cloud database | DynamoDB: students, records (with stream), summary, connections |
| Processing + analytics | Lambda `processor` (CSV load) and `stream` (running summaries per class/section) |
| Real-time update service | API Gateway WebSocket API + Lambda `ws` |
| Authentication | Cognito user pool with roles |
| Cloud storage | S3 data bucket (private, encrypted) |
| Monitoring | CloudWatch log groups, retention, alarms |

Deploy: `./deploy.sh` and enter the admin email/password when prompted (or set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the environment). The deployment creates the Cognito admin user, assigns it to the `admin` group, sets its permanent password, and configures the dashboard login. Remove: `./deploy.sh destroy`. Step-by-step guide: `Deployment-Guide.pdf`.

API (all need `Authorization: <ID token>`): `GET /students`, `GET /records`, `GET /summary`, `POST /records` (teacher or admin). Never commit `dashboard/config.js`, keys or passwords.
