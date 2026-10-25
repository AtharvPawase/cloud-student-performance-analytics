import json, os
import boto3
from boto3.dynamodb.types import TypeDeserializer

ddb, des = boto3.resource("dynamodb"), TypeDeserializer()
summary, conns = ddb.Table(os.environ["SUMMARY_TABLE"]), ddb.Table(os.environ["CONNECTIONS_TABLE"])
api = boto3.client("apigatewaymanagementapi", endpoint_url=os.environ["WS_ENDPOINT"])
PASS = int(os.environ["PASS_MARKS"])
FIELDS = ("cls", "sec", "subject", "period", "sem", "date", "exam", "marks", "att")


def img(i):
    return {k: des.deserialize(v) for k, v in i.items()} if i else None


def handler(event, context):
    agg, fresh = {}, []
    for rec in event["Records"]:
        old, new = img(rec["dynamodb"].get("OldImage")), img(rec["dynamodb"].get("NewImage"))
        for im, sign in ((old, -1), (new, 1)):
            if not im:
                continue
            for key in (f'{im["cls"]}|{im["sec"]}', "ALL"):
                v = agg.setdefault(key, [0, 0, 0, 0])
                v[0] += sign
                v[1] += im["marks"] * sign
                v[2] += im["att"] * sign
                v[3] += int(im["marks"] >= PASS) * sign
        if new:
            fresh.append({"sid": new["studentId"], **{k: new[k] for k in FIELDS}})
    for key, (n, m, a, p) in agg.items():  # keep running totals the dashboard summary needs
        summary.update_item(Key={"pk": key}, UpdateExpression="ADD n :n, marksSum :m, attSum :a, passN :p",
                            ExpressionAttributeValues={":n": n, ":m": m, ":a": a, ":p": p})
    if fresh:  # push the new rows to every open dashboard
        data = json.dumps({"type": "records", "items": fresh}, default=float).encode()
        for c in conns.scan()["Items"]:
            try:
                api.post_to_connection(ConnectionId=c["connectionId"], Data=data)
            except api.exceptions.GoneException:
                conns.delete_item(Key={"connectionId": c["connectionId"]})
    return {"processed": len(event["Records"])}
