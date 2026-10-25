import json, os
from decimal import Decimal
import boto3

ddb = boto3.resource("dynamodb")
T = {k: ddb.Table(os.environ[k]) for k in ("STUDENTS_TABLE", "RECORDS_TABLE", "SUMMARY_TABLE")}


def scan(t):
    out, kw = [], {}
    while True:
        r = t.scan(**kw)
        out += r["Items"]
        if "LastEvaluatedKey" not in r:
            return out
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def resp(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, default=float)}


def handler(event, context):
    route = event["routeKey"]
    groups = event["requestContext"]["authorizer"]["jwt"]["claims"].get("cognito:groups", "")
    if route == "GET /students":
        return resp(200, scan(T["STUDENTS_TABLE"]))
    if route == "GET /records":
        return resp(200, scan(T["RECORDS_TABLE"]))
    if route == "GET /summary":
        return resp(200, scan(T["SUMMARY_TABLE"]))
    if route == "POST /records":
        if "teacher" not in groups and "admin" not in groups:
            return resp(403, {"error": "Only teachers and admins can save marks"})
        try:
            b = json.loads(event["body"])
            m, a = Decimal(str(b["marks"])), Decimal(str(b["attendance"]))
            if not (0 <= m <= 100 and 0 <= a <= 100):
                raise ValueError("marks and attendance must be between 0 and 100")
            st = T["STUDENTS_TABLE"].get_item(Key={"studentId": b["studentId"]}).get("Item")
            if not st:
                raise ValueError("unknown student")
            # same student + subject + period overwrites the old row, so duplicates cannot occur
            T["RECORDS_TABLE"].put_item(Item={
                "studentId": b["studentId"], "recordId": f'{b["period"]}#{b["subject"]}',
                "cls": st["cls"], "sec": st["sec"], "subject": b["subject"], "period": b["period"],
                "sem": b["sem"], "date": b["date"], "exam": b["exam"], "marks": m, "att": a})
        except (KeyError, ValueError, ArithmeticError) as e:
            return resp(400, {"error": f"Invalid record: {e}"})
        return resp(201, {"saved": True})
    return resp(404, {"error": "Not found"})
