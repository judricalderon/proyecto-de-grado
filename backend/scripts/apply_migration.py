import argparse
import os
from pathlib import Path

import boto3


def split_statements(sql):
    statements, current = [], []
    quote = None
    line_comment = block_comment = False
    index = 0
    while index < len(sql):
        char = sql[index]
        following = sql[index:index + 2]
        if line_comment:
            current.append(char)
            if char == "\n": line_comment = False
        elif block_comment:
            current.append(char)
            if following == "*/": current.append("/"); index += 1; block_comment = False
        elif quote:
            current.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    current.append(quote); index += 1
                else: quote = None
        elif following == "--":
            current.extend(following); index += 1; line_comment = True
        elif following == "/*":
            current.extend(following); index += 1; block_comment = True
        elif char in ("'", '"'):
            quote = char; current.append(char)
        elif char == ";":
            statement = "".join(current).strip()
            if statement: statements.append(statement)
            current = []
        else: current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail: statements.append(tail)
    return [s for s in statements if s.upper() not in ("BEGIN", "COMMIT")]


def apply(path, cluster_arn, secret_arn, database_name):
    client = boto3.client("rds-data")
    transaction = client.begin_transaction(resourceArn=cluster_arn, secretArn=secret_arn, database=database_name)["transactionId"]
    try:
        for sql in split_statements(path.read_text(encoding="utf-8")):
            client.execute_statement(resourceArn=cluster_arn, secretArn=secret_arn, database=database_name, transactionId=transaction, sql=sql)
        client.commit_transaction(resourceArn=cluster_arn, secretArn=secret_arn, transactionId=transaction)
    except Exception:
        client.rollback_transaction(resourceArn=cluster_arn, secretArn=secret_arn, transactionId=transaction)
        raise


def main():
    parser = argparse.ArgumentParser(description="Aplica una migración SQL mediante RDS Data API")
    parser.add_argument("file", type=Path)
    parser.add_argument("--cluster-arn", default=os.environ.get("DB_CLUSTER_ARN"))
    parser.add_argument("--secret-arn", default=os.environ.get("DB_SECRET_ARN"))
    parser.add_argument("--database", default=os.environ.get("DB_NAME"))
    args = parser.parse_args()
    if not all((args.cluster_arn, args.secret_arn, args.database)):
        parser.error("defina DB_CLUSTER_ARN, DB_SECRET_ARN y DB_NAME o use los parámetros equivalentes")
    apply(args.file, args.cluster_arn, args.secret_arn, args.database)


if __name__ == "__main__":
    main()
