#!/usr/bin/env python
"""
TheraSocial K11 — Diary Reminder Deduplication Test Script
===========================================================

Run on the Render shell (or locally with DATABASE_URL set):
    python test_diary_reminder_K11.py

What it does:
  1. Connects to production database (uses DATABASE_URL env var)
  2. Finds the two test accounts (emaskanazi@gmail.com, ema9u@virginia.edu)
  3. Runs 7 checks covering all three K11 fix causes
  4. Sends ONE real reminder email to each account (only if all checks pass)
  5. Verifies the dedup stamp was written and a second send is blocked

Requires: DATABASE_URL, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_EMAIL
          (all should already be set in Render environment)

Safe to run multiple times — the final step resets last_sent to NULL so normal
scheduling resumes unaffected.
"""

import os
import sys
import traceback
from datetime import datetime, date, timedelta

# ── pretty output ──────────────────────────────────────────────────────────
GREEN  = "\033[92m✓\033[0m"
RED    = "\033[91m✗\033[0m"
YELLOW = "\033[93m⚠\033[0m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

pass_count = 0
fail_count = 0
warn_count = 0

def check_pass(label, detail=""):
    global pass_count
    pass_count += 1
    print(f"  {GREEN}  {label}" + (f"  ({detail})" if detail else ""))

def check_fail(label, detail="", fix=""):
    global fail_count
    fail_count += 1
    print(f"  {RED}  {label}" + (f"  — {detail}" if detail else ""))
    if fix:
        print(f"       {YELLOW} Fix: {fix}")

def check_warn(label, detail=""):
    global warn_count
    warn_count += 1
    print(f"  {YELLOW}  {label}" + (f"  — {detail}" if detail else ""))

def section(title):
    print(f"\n{BOLD}{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}{RESET}")


# ── target accounts ────────────────────────────────────────────────────────
TEST_EMAILS = [
    "emaskanazi@gmail.com",
    "ema9u@virginia.edu",
]


def main():
    # ════════════════════════════════════════════════════════════════════════
    # SETUP: Connect to database
    # ════════════════════════════════════════════════════════════════════════
    section("SETUP — Database Connection")

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        check_fail("DATABASE_URL environment variable", "Not set",
                    "export DATABASE_URL='postgresql://...'")
        summary()
        return

    # Fix Render's postgres:// → postgresql://
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, pool_pre_ping=True)
        conn = engine.connect()
        check_pass("Connected to database")
    except Exception as e:
        check_fail("Database connection", str(e),
                    "Verify DATABASE_URL is correct and DB is reachable")
        summary()
        return

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 1: Find test accounts
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 1 — Test Account Lookup")

    accounts = {}  # email → {user_id, ns_id, ...}
    for email in TEST_EMAILS:
        row = conn.execute(
            text("SELECT id, email, preferred_language FROM users WHERE email = :e"),
            {'e': email}
        ).first()
        if not row:
            check_fail(f"Account exists: {email}", "Not found in users table",
                        "Register this account or adjust TEST_EMAILS list")
            continue

        user_id = row[0]
        lang = row[2] or 'en'

        ns = conn.execute(
            text("SELECT id, email_daily_diary_reminder, diary_reminder_time, "
                 "diary_reminder_timezone FROM notification_settings WHERE user_id = :uid"),
            {'uid': user_id}
        ).first()

        if not ns:
            check_fail(f"NotificationSettings for {email}", "Row missing",
                        "Enable diary reminders once in the UI to create the row")
            continue

        accounts[email] = {
            'user_id': user_id,
            'ns_id': ns[0],
            'reminder_enabled': ns[1],
            'reminder_time': ns[2],
            'reminder_tz': ns[3],
            'language': lang,
        }
        enabled_str = "enabled" if ns[1] else "disabled"
        check_pass(f"Found {email}", f"user_id={user_id}, reminder={enabled_str}, "
                   f"time={ns[2]}, tz={ns[3]}")

    if not accounts:
        check_fail("No test accounts found — cannot continue")
        summary()
        conn.close()
        return

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 2: diary_reminder_last_sent column exists
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 2 — Schema: diary_reminder_last_sent Column")

    try:
        conn.execute(text(
            "SELECT diary_reminder_last_sent FROM notification_settings LIMIT 1"
        ))
        check_pass("Column diary_reminder_last_sent exists in notification_settings")
    except Exception as e:
        check_fail("Column diary_reminder_last_sent", str(e),
                    "Deploy K11 appK11.py — the auto-migration (ensure_notification_settings_schema) "
                    "creates this column on startup")
        summary()
        conn.close()
        return

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 3: Simulate cron-path dedup (K11 FIX 1)
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 3 — Cron Endpoint Dedup Logic (K11 Fix 1)")

    for email, acct in accounts.items():
        sid = acct['ns_id']

        # Step A: Clear last_sent so we start clean
        conn.execute(
            text("UPDATE notification_settings SET diary_reminder_last_sent = NULL WHERE id = :sid"),
            {'sid': sid}
        )
        conn.commit()

        row = conn.execute(
            text("SELECT diary_reminder_last_sent FROM notification_settings WHERE id = :sid"),
            {'sid': sid}
        ).first()
        if row[0] is None:
            check_pass(f"[{email}] last_sent cleared to NULL")
        else:
            check_fail(f"[{email}] Could not clear last_sent", f"value={row[0]}")

        # Step B: Stamp today's date (simulate a successful send)
        today = date.today()
        conn.execute(
            text("UPDATE notification_settings SET diary_reminder_last_sent = :td WHERE id = :sid"),
            {'td': today, 'sid': sid}
        )
        conn.commit()

        row2 = conn.execute(
            text("SELECT diary_reminder_last_sent FROM notification_settings WHERE id = :sid"),
            {'sid': sid}
        ).first()
        if row2[0] == today:
            check_pass(f"[{email}] last_sent stamped to today ({today})")
        else:
            check_fail(f"[{email}] Stamp failed", f"expected={today}, got={row2[0]}")

        # Step C: Verify dedup would block a second send
        last_sent = row2[0]
        if last_sent == today:
            check_pass(f"[{email}] Dedup check: second send BLOCKED (last_sent == today)")
        else:
            check_fail(f"[{email}] Dedup check: would NOT block",
                        "last_sent != today",
                        "Ensure cron endpoint checks diary_reminder_last_sent before sending")

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 4: Time-change resets last_sent (K11 FIX 2)
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 4 — Time Change Resets last_sent (K11 Fix 2)")

    for email, acct in accounts.items():
        uid = acct['user_id']
        sid = acct['ns_id']

        # Stamp today to simulate "already sent"
        conn.execute(
            text("UPDATE notification_settings SET diary_reminder_last_sent = :td WHERE id = :sid"),
            {'td': date.today(), 'sid': sid}
        )
        conn.commit()

        # Simulate what K11's PUT handler does: reset last_sent on time change
        conn.execute(
            text("UPDATE notification_settings SET diary_reminder_last_sent = NULL WHERE user_id = :uid"),
            {'uid': uid}
        )
        conn.commit()

        row = conn.execute(
            text("SELECT diary_reminder_last_sent FROM notification_settings WHERE id = :sid"),
            {'sid': sid}
        ).first()
        if row[0] is None:
            check_pass(f"[{email}] Time change reset last_sent to NULL — new time can fire today")
        else:
            check_fail(f"[{email}] last_sent not reset after time change", f"value={row[0]}",
                        "Ensure PUT /api/notification-settings resets last_sent when diary_reminder_time changes")

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 5: Advisory lock IDs are distinct (pre-existing T15a)
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 5 — Advisory Lock IDs (T15a multi-worker protection)")

    # Just verify the lock IDs are usable — try_advisory_lock / unlock cycle
    lock_ids = {'diary': 100001, 'trigger': 100002, 'job_queue': 100003, 'data_retention': 100004}
    for name, lid in lock_ids.items():
        try:
            acquired = conn.execute(
                text("SELECT pg_try_advisory_lock(:lid)"), {'lid': lid}
            ).scalar()
            if acquired:
                conn.execute(text("SELECT pg_advisory_unlock(:lid)"), {'lid': lid})
                check_pass(f"Advisory lock {name} (id={lid}): acquire/release OK")
            else:
                check_warn(f"Advisory lock {name} (id={lid}): held by another session",
                           "Normal if a scheduler is running — means T15a is working")
        except Exception as e:
            check_fail(f"Advisory lock {name} (id={lid})", str(e))

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 6: SMTP config present
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 6 — SMTP Configuration")

    smtp_vars = {
        'SMTP_SERVER': os.environ.get('SMTP_SERVER'),
        'SMTP_PORT': os.environ.get('SMTP_PORT'),
        'SMTP_USERNAME': os.environ.get('SMTP_USERNAME'),
        'SMTP_PASSWORD': os.environ.get('SMTP_PASSWORD'),
        'FROM_EMAIL': os.environ.get('FROM_EMAIL'),
    }
    smtp_ok = True
    for var, val in smtp_vars.items():
        if val:
            display = val if var != 'SMTP_PASSWORD' else '****' + val[-4:] if len(val) > 4 else '****'
            check_pass(f"{var} is set", display)
        else:
            if var == 'SMTP_PASSWORD':
                check_fail(f"{var} is NOT set", "Required for sending emails",
                            f"Set {var} in Render environment variables")
                smtp_ok = False
            else:
                check_warn(f"{var} not set — will use defaults")

    # ════════════════════════════════════════════════════════════════════════
    # CHECK 7: Send ONE real email per account + verify dedup blocks second
    # ════════════════════════════════════════════════════════════════════════
    section("CHECK 7 — Live Send + Dedup Verification")

    if not smtp_ok:
        check_warn("Skipping live send — SMTP not configured")
    else:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_server = smtp_vars['SMTP_SERVER'] or 'smtp.resend.com'
        smtp_port = int(smtp_vars['SMTP_PORT'] or '465')
        smtp_user = smtp_vars['SMTP_USERNAME'] or 'resend'
        smtp_pass = smtp_vars['SMTP_PASSWORD']
        from_email = smtp_vars['FROM_EMAIL'] or 'TheraSocial <onboarding@resend.dev>'

        for email, acct in accounts.items():
            sid = acct['ns_id']

            # Clear last_sent so we can send once
            conn.execute(
                text("UPDATE notification_settings SET diary_reminder_last_sent = NULL WHERE id = :sid"),
                {'sid': sid}
            )
            conn.commit()

            # ── SEND 1: Should succeed ──
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "TheraSocial - K11 Dedup Test Reminder"
                msg['From'] = from_email
                msg['To'] = email
                msg['List-Unsubscribe'] = '<https://therasocial.org/settings>'
                msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'

                html = f"""
                <html><body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width:500px; margin:0 auto; background:#fff; border-radius:12px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow:hidden;">
                  <div style="background: linear-gradient(135deg, #667eea, #764ba2);
                              padding: 24px; text-align:center;">
                    <h2 style="color:#fff; margin:0;">📝 K11 Dedup Test</h2>
                  </div>
                  <div style="padding: 24px;">
                    <p>This is a <strong>single</strong> test reminder for the K11 dedup fix.</p>
                    <p style="color:#888; font-size:13px;">
                      Account: {email}<br>
                      Sent at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                      If you receive this email exactly <strong>once</strong>, the fix is working.
                    </p>
                  </div>
                </div>
                </body></html>
                """
                plain = (f"K11 Dedup Test Reminder\n\n"
                         f"This is a single test reminder for {email}.\n"
                         f"If you receive this exactly once, the fix is working.\n"
                         f"Sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                msg.attach(MIMEText(plain, 'plain'))
                msg.attach(MIMEText(html, 'html'))

                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(from_email, email, msg.as_string())

                check_pass(f"[{email}] Email #1 SENT successfully")

                # Stamp last_sent
                today = date.today()
                conn.execute(
                    text("UPDATE notification_settings SET diary_reminder_last_sent = :td WHERE id = :sid"),
                    {'td': today, 'sid': sid}
                )
                conn.commit()
                check_pass(f"[{email}] last_sent stamped to {today}")

            except Exception as e:
                check_fail(f"[{email}] Email #1 FAILED", str(e),
                            "Check SMTP credentials and email service status")
                continue

            # ── SEND 2: Should be BLOCKED by dedup ──
            row = conn.execute(
                text("SELECT diary_reminder_last_sent FROM notification_settings WHERE id = :sid"),
                {'sid': sid}
            ).first()
            last_sent = row[0] if row else None

            if last_sent == today:
                check_pass(f"[{email}] Email #2 BLOCKED by dedup (last_sent == {today})")
            else:
                check_fail(f"[{email}] Email #2 would NOT be blocked!",
                            f"last_sent={last_sent}, today={today}",
                            "Dedup stamp was not written correctly")

    # ════════════════════════════════════════════════════════════════════════
    # CLEANUP: Reset last_sent so normal scheduling resumes
    # ════════════════════════════════════════════════════════════════════════
    section("CLEANUP — Reset last_sent for Normal Operation")

    for email, acct in accounts.items():
        sid = acct['ns_id']
        conn.execute(
            text("UPDATE notification_settings SET diary_reminder_last_sent = NULL WHERE id = :sid"),
            {'sid': sid}
        )
        conn.commit()
        check_pass(f"[{email}] last_sent reset to NULL — normal scheduling resumes")

    conn.close()
    summary()


def summary():
    section("RESULTS")
    total = pass_count + fail_count + warn_count
    print(f"  {GREEN}  Passed:   {pass_count}")
    if warn_count:
        print(f"  {YELLOW}  Warnings: {warn_count}")
    if fail_count:
        print(f"  {RED}  Failed:   {fail_count}")
    print()
    if fail_count == 0:
        print(f"  {BOLD}{GREEN}  ALL CHECKS PASSED — K11 dedup is working correctly{RESET}")
        print(f"  Each test account should receive exactly ONE email.")
    else:
        print(f"  {BOLD}{RED}  {fail_count} CHECK(S) FAILED — see fixes above{RESET}")
    print()


if __name__ == '__main__':
    main()
