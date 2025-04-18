#!/usr/bin/env python3
"""Invite a user to Supabase Auth via the service role key.

Usage:
    python scripts/invite_user.py --email tom@thomason.com --name "Thomas Thomason"
Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in the environment.
"""
import argparse
import os
import sys
from tools.supabase_client import SupabaseClient


def main():
    parser = argparse.ArgumentParser(description="Invite user via Supabase Auth (admin.create_user)")
    parser.add_argument('--email', required=True, help='User email')
    parser.add_argument('--name', default='', help='User full name (optional)')
    parser.add_argument('--password', default=None, help='Optional initial password (if omitted Supabase will send invite email)')
    args = parser.parse_args()

    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')

    if not supabase_url or not service_key:
        print('SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in the environment', file=sys.stderr)
        sys.exit(1)

    # Use SupabaseClient wrapper to get underlying client
    sb_wrapper = SupabaseClient(supabase_url, service_key)
    client = sb_wrapper.client

    try:
        if args.password:
            # Directly create user with password (no email needed)
            user_data = {
                "email": args.email,
                "password": args.password,
                "email_confirm": True,
                "user_metadata": {"full_name": args.name}
            }
            res = client.auth.admin.create_user(user_data)
            print('User created with password (no invite email):', res.user if hasattr(res, 'user') else res)
        else:
            # Send invite email via Supabase helper
            res = client.auth.admin.invite_user_by_email(args.email, {"user_metadata": {"full_name": args.name}})
            print('Invite email triggered:', res)
    except Exception as e:
        print('Error inviting user:', e, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main() 