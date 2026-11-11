"""INSTRUCTOR ONLY - create / delete one Bedrock API key per student.

Each long-term Bedrock API key belongs to an IAM user, so this script creates
`workshop-student-01..N` IAM users, gives each a minimal inline policy (invoke models only),
and generates a Bedrock API key that expires after N days.

Requirements (instructor machine only):
    pip install boto3
    AWS credentials with IAM admin rights (e.g. `aws configure` or `aws sso login`)

Usage:
    python docs/instructor/bedrock_keys.py create --count 12 --days 7
    python docs/instructor/bedrock_keys.py delete            # after the workshop!

The keys are written to `students.keys.csv` (git-ignored). Send each student their own line.
"""

from __future__ import annotations

import argparse
import csv
import json

import boto3

PREFIX = "workshop-student-"
TAG = {"Key": "purpose", "Value": "agentic-ai-workshop"}
POLICY_NAME = "workshop-bedrock-invoke-only"

# Minimal permissions: call models, nothing else. Tighten Resource to specific model /
# inference-profile ARNs if you want to restrict which models students can use.
POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:CallWithBearerToken",
            ],
            "Resource": "*",
        }
    ],
}

iam = boto3.client("iam")


def create(count: int, days: int, out: str) -> None:
    rows = []
    for i in range(1, count + 1):
        user = f"{PREFIX}{i:02d}"
        try:
            iam.create_user(UserName=user, Tags=[TAG])
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"{user}: already exists, adding a new key")
        iam.put_user_policy(UserName=user, PolicyName=POLICY_NAME, PolicyDocument=json.dumps(POLICY))
        cred = iam.create_service_specific_credential(
            UserName=user, ServiceName="bedrock.amazonaws.com", CredentialAgeDays=days
        )["ServiceSpecificCredential"]
        # Field name differs between boto3 versions.
        key = cred.get("ServiceApiKeyValue") or cred.get("ServiceCredentialSecret")
        rows.append({"user": user, "api_key": key, "expires": str(cred.get("ExpirationDate", ""))})
        print(f"{user}: key created")

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user", "api_key", "expires"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} keys to {out}. Keep this file private!")


def delete() -> None:
    paginator = iam.get_paginator("list_users")
    users = [u["UserName"] for page in paginator.paginate() for u in page["Users"]
             if u["UserName"].startswith(PREFIX)]
    for user in users:
        for c in iam.list_service_specific_credentials(UserName=user)["ServiceSpecificCredentials"]:
            iam.delete_service_specific_credential(
                UserName=user, ServiceSpecificCredentialId=c["ServiceSpecificCredentialId"]
            )
        for name in iam.list_user_policies(UserName=user)["PolicyNames"]:
            iam.delete_user_policy(UserName=user, PolicyName=name)
        iam.delete_user(UserName=user)
        print(f"{user}: deleted")
    print(f"Deleted {len(users)} users.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create")
    c.add_argument("--count", type=int, default=12)
    c.add_argument("--days", type=int, default=7, help="key lifetime in days")
    c.add_argument("--out", default="students.keys.csv")
    sub.add_parser("delete")
    a = p.parse_args()
    create(a.count, a.days, a.out) if a.cmd == "create" else delete()
