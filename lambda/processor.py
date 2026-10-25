import csv, io, os, urllib.parse
from decimal import Decimal
import boto3

s3, ddb = boto3.client("s3"), boto3.resource("dynamodb")
students, records = ddb.Table(os.environ["STUDENTS_TABLE"]), ddb.Table(os.environ["RECORDS_TABLE"])


def handler(event, context):
    n = 0
    for e in event["Records"]:
        bucket, key = e["s3"]["bucket"]["name"], urllib.parse.unquote_plus(e["s3"]["object"]["key"])
        text = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8-sig")
        with students.batch_writer(overwrite_by_pkeys=["studentId"]) as sw, \
             records.batch_writer(overwrite_by_pkeys=["studentId", "recordId"]) as rw:
            for r in csv.DictReader(io.StringIO(text)):
                m, a = Decimal(r["marks"]), Decimal(r["attendance"])
                if not (0 <= m <= 100 and 0 <= a <= 100):
                    continue  # validation: marks and attendance must be 0-100
                sw.put_item(Item={"studentId": r["student_id"], "roll": r["roll"], "name": r["name"],
                                  "cls": r["class"], "sec": r["section"]})
                rw.put_item(Item={"studentId": r["student_id"], "recordId": f'{r["period"]}#{r["subject"]}',
                                  "cls": r["class"], "sec": r["section"], "subject": r["subject"],
                                  "period": r["period"], "sem": r["semester"], "date": r["date"],
                                  "exam": r["exam"], "marks": m, "att": a})
                n += 1
    print(f"Loaded {n} records")
    return {"loaded": n}
