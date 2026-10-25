import os, time
import boto3

cognito = boto3.client("cognito-idp")
conns = boto3.resource("dynamodb").Table(os.environ["CONNECTIONS_TABLE"])


def handler(event, context):
    rc = event["requestContext"]
    if rc["routeKey"] == "$connect":
        try:  # only signed-in users may listen: the access token must be valid
            cognito.get_user(AccessToken=event["queryStringParameters"]["token"])
        except Exception:
            return {"statusCode": 401}
        conns.put_item(Item={"connectionId": rc["connectionId"], "ttl": int(time.time()) + 7200})
    else:
        conns.delete_item(Key={"connectionId": rc["connectionId"]})
    return {"statusCode": 200}
