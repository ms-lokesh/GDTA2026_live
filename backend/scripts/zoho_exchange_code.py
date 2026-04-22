#!/usr/bin/env python3
import argparse
import os
import sys

import requests
from dotenv import load_dotenv


def parse_args():
    parser = argparse.ArgumentParser(
        description="Exchange Zoho authorization code for refresh token."
    )
    parser.add_argument("--code", required=True, help="One-time Zoho authorization code")
    parser.add_argument(
        "--redirect-uri",
        default=os.getenv("ZOHO_REDIRECT_URI", "http://localhost:8000/zoho/callback"),
        help="Redirect URI configured in Zoho OAuth app",
    )
    parser.add_argument(
        "--accounts-base-url",
        default=os.getenv("ZOHO_ACCOUNTS_BASE_URL", "https://accounts.zoho.in"),
        help="Zoho accounts base URL (e.g. https://accounts.zoho.in)",
    )
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    client_id = os.getenv("ZOHO_CLIENT_ID", "").strip()
    client_secret = os.getenv("ZOHO_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        print("ERROR: ZOHO_CLIENT_ID or ZOHO_CLIENT_SECRET missing in .env", file=sys.stderr)
        sys.exit(1)

    token_url = f"{args.accounts_base_url.rstrip('/')}/oauth/v2/token"
    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": args.redirect_uri,
            "code": args.code,
        },
        timeout=20,
    )

    payload = {}
    try:
        payload = response.json() or {}
    except Exception:
        pass

    if response.status_code >= 400:
        print("ERROR: Zoho token exchange failed", file=sys.stderr)
        print(f"HTTP {response.status_code}", file=sys.stderr)
        print(payload if payload else response.text, file=sys.stderr)
        sys.exit(1)

    refresh_token = payload.get("refresh_token")
    access_token = payload.get("access_token")

    if not refresh_token:
        print("ERROR: No refresh_token returned. This usually means the code is expired/used.", file=sys.stderr)
        print(payload, file=sys.stderr)
        sys.exit(1)

    print("SUCCESS")
    print(f"refresh_token={refresh_token}")
    print(f"access_token={access_token}")
    print("\nPaste this in backend/.env:")
    print(f"ZOHO_REFRESH_TOKEN={refresh_token}")


if __name__ == "__main__":
    main()
