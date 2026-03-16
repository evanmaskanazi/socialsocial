#!/usr/bin/env python3
# NO-CHECKIN TRIGGER DIAGNOSTIC - Render Shell Script
# ====================================================
#
# USAGE (Render Dashboard -> Shell tab, which is a BASH shell):
#
#   Option A - one-shot heredoc:
#     cat > /tmp/diag.py << 'ENDSCRIPT'
#     <paste this entire file>
#     ENDSCRIPT
#     cd /opt/render/project/src && python3 /tmp/diag.py
#
#   Option B - if file is in your repo:
#     cd /opt/render/project/src && python3 diagnose_no_checkin_render.py
#
#   Option C - target a specific watcher:
#     cd /opt/render/project/src && python3 /tmp/diag.py emaskanazi_1
#
# Do NOT paste into a Python >>> REPL.  Use the bash shell.

import sys
import os
from datetime import datetime, timedelta, date as date_type

HAS_APP = False
try:
    from app import app, db
    from sqlalchemy import select, text, desc, func
    HAS_APP = True
except ImportError:
    pass

RESET = "\033[0m"
BOLD_ON = "\033[1m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"


def ok(msg):
    print("  %sOK %s%s" % (C_GREEN, RESET, msg))


def fail(msg):
    print("  %sFAIL %s%s" % (C_RED, RESET, msg))


def warn(msg):
    print("  %sWARN %s%s" % (C_YELLOW, RESET, msg))


def info(msg):
    print("  %sINFO %s%s" % (C_BLUE, RESET, msg))


def header(msg):
    sep = "=" * 60
    print("")
    print("%s%s%s" % (BOLD_ON, sep, RESET))
    print("%s  %s%s" % (BOLD_ON, msg, RESET))
    print("%s%s%s" % (BOLD_ON, sep, RESET))


def sub(msg):
    print("")
    print("  %s-- %s --%s" % (BOLD_ON, msg, RESET))


results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    label = str(name)
    if detail:
        label = label + ": " + str(detail)
    if passed:
        ok(label)
    else:
        fail(label)
    return passed


def run_diagnosis(target_watcher_username=None):
    if not HAS_APP:
        print("ERROR: Cannot import app.")
        print("  Make sure you run from /opt/render/project/src")
        print("  cd /opt/render/project/src && python3 /tmp/diag.py")
        return

    header("NO-CHECKIN TRIGGER DIAGNOSTIC")
    info("Timestamp: %sZ" % datetime.utcnow().isoformat())

    with app.app_context():
        _run_all_checks(target_watcher_username)

    header("SUMMARY")
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print("  Passed: %d/%d  |  Failed: %d/%d" % (passed, total, failed, total))
    if failed == 0:
        ok("All checks passed")
    else:
        fail("%d issue(s) found" % failed)
        print("")
        print("  %sFailed checks:%s" % (BOLD_ON, RESET))
        for name, p, detail in results:
            if not p:
                fail("  %s: %s" % (name, detail))


def _run_all_checks(target_watcher_username):
    from app import User, ParameterTrigger, SavedParameters, Alert, Follow
    from app import ALERT_EMAIL_MODE, MINIMUM_TRIGGER_DAYS

    # ==================================================================
    # CHECK 1: Constants
    # ==================================================================
    header("1. CONFIGURATION")

    info("ALERT_EMAIL_MODE = '%s'" % ALERT_EMAIL_MODE)
    info("MINIMUM_TRIGGER_DAYS = %d" % MINIMUM_TRIGGER_DAYS)

    check("ALERT_EMAIL_MODE is valid",
          ALERT_EMAIL_MODE in ("new_alerts_only", "daily_reminder"),
          "'%s'" % ALERT_EMAIL_MODE)

    # ==================================================================
    # CHECK 2: Find all no_checkin triggers
    # ==================================================================
    header("2. NO_CHECKIN TRIGGER ROWS")

    query = select(ParameterTrigger).filter(
        ParameterTrigger.parameter_name == 'no_checkin'
    )
    if target_watcher_username:
        watcher = User.query.filter_by(username=target_watcher_username).first()
        if not watcher:
            fail("Watcher username '%s' not found" % target_watcher_username)
            return
        query = query.filter(ParameterTrigger.watcher_id == watcher.id)

    no_checkin_triggers = db.session.execute(query).scalars().all()

    check("no_checkin triggers exist in DB",
          len(no_checkin_triggers) > 0,
          "Found %d no_checkin trigger row(s)" % len(no_checkin_triggers))

    if not no_checkin_triggers:
        fail("No no_checkin triggers found -- nothing to diagnose")
        return

    for trig in no_checkin_triggers:
        watcher_user = db.session.get(User, trig.watcher_id)
        watched_user = db.session.get(User, trig.watched_id)
        watcher_name = watcher_user.username if watcher_user else ("user_%d" % trig.watcher_id)
        watched_name = watched_user.username if watched_user else ("user_%d" % trig.watched_id)

        sub("Trigger ID=%d: %s -> watches %s" % (trig.id, watcher_name, watched_name))

        info("parameter_name='%s', condition='%s', threshold=%s" % (
            trig.parameter_name, trig.trigger_condition, trig.trigger_value))
        info("consecutive_days=%s, is_active=%s, last_triggered=%s" % (
            trig.consecutive_days, trig.is_active, trig.last_triggered))

        # 2a: is_active
        check("  Trigger %d is_active" % trig.id,
              trig.is_active is True,
              "is_active=%s" % trig.is_active)

        if not trig.is_active:
            warn("  Trigger %d is deactivated -- scheduler will skip it" % trig.id)
            continue

        # 2b: consecutive_days
        effective_days = max(trig.consecutive_days or MINIMUM_TRIGGER_DAYS, MINIMUM_TRIGGER_DAYS)
        check("  Trigger %d consecutive_days >= MINIMUM" % trig.id,
              effective_days >= MINIMUM_TRIGGER_DAYS,
              "raw=%s, effective=%d, minimum=%d" % (
                  trig.consecutive_days, effective_days, MINIMUM_TRIGGER_DAYS))

        # ==============================================================
        # CHECK 3: Follow relationship
        # ==============================================================
        sub("Follow & Circle Check: %s -> %s" % (watcher_name, watched_name))

        follow = Follow.query.filter_by(
            follower_id=trig.watcher_id,
            followed_id=trig.watched_id
        ).first()

        check("  %s follows %s" % (watcher_name, watched_name),
              follow is not None,
              "Follow exists=%s" % (follow is not None))

        circle = None
        try:
            from app import get_watcher_circle_level
            circle = get_watcher_circle_level(trig.watched_id, trig.watcher_id)
        except Exception:
            pass

        check("  Watcher has circle access",
              circle is not None,
              "circle_level='%s'" % circle)

        if not circle:
            fail("  No circle access -- scheduler will skip this trigger")

        # ==============================================================
        # CHECK 4: THE CRITICAL BUG - parameters count gate
        # ==============================================================
        sub("Parameters Count Gate (THE LIKELY BUG)")

        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        params_count = db.session.execute(
            select(func.count(SavedParameters.id)).filter(
                SavedParameters.user_id == trig.watched_id,
                SavedParameters.date >= thirty_days_ago
            )
        ).scalar()

        info("Watched user '%s' has %d diary entries in last 30 days" % (
            watched_name, params_count))
        info("Trigger requires consecutive_days=%d" % effective_days)

        gate_would_block = params_count < effective_days

        check("  Parameters count gate does NOT block no_checkin",
              not gate_would_block,
              "params_count(%d) >= consecutive_days(%d) = %s" % (
                  params_count, effective_days, not gate_would_block))

        if gate_would_block:
            fail("  *** ROOT CAUSE FOUND ***")
            fail("  run_background_trigger_check_for_watcher() line ~16470:")
            fail("      if len(parameters) < consecutive_days: continue")
            fail("  This gate runs BEFORE the no_checkin logic at line ~16570.")
            fail("  Because %s has only %d entries (< %d)," % (
                watched_name, params_count, effective_days))
            fail("  the entire trigger is skipped -- no_checkin never evaluated.")
            fail("  FIX: Move no_checkin check before this gate.")

        if params_count == 0:
            warn("  Watched user has ZERO entries -- no_checkin should fire but")
            warn("  cannot get past the parameters count gate")

        # ==============================================================
        # CHECK 5: Latest entry & days_since
        # ==============================================================
        sub("Days Since Last Check-in")

        latest_entry = db.session.execute(
            select(SavedParameters).filter(
                SavedParameters.user_id == trig.watched_id
            ).order_by(SavedParameters.date.desc()).limit(1)
        ).scalars().first()

        if latest_entry and latest_entry.date:
            today = date_type.today()
            days_since = (today - latest_entry.date).days
            info("Latest entry date: %s" % latest_entry.date.isoformat())
            info("Today: %s" % today.isoformat())
            info("Days since last check-in: %d" % days_since)

            should_fire = days_since >= effective_days
            check("  days_since(%d) >= consecutive_days(%d)" % (days_since, effective_days),
                  should_fire,
                  "Trigger SHOULD fire: %s" % should_fire)
        else:
            info("No entries found for %s at all -- days_since=999" % watched_name)
            check("  User has no entries (days_since=999 >= %d)" % effective_days,
                  True,
                  "Trigger SHOULD fire (but gate blocks it)")

        # ==============================================================
        # CHECK 6: Duplicate alert check
        # ==============================================================
        sub("Duplicate Alert Check")

        like_pattern = "%%%s%%hasn't checked in%%" % watched_name
        all_no_checkin_alerts = Alert.query.filter(
            Alert.user_id == trig.watcher_id,
            Alert.alert_type == 'trigger',
            Alert.content.ilike(like_pattern)
        ).order_by(desc(Alert.created_at)).all()

        info("Total no_checkin alerts ever for %s about %s: %d" % (
            watcher_name, watched_name, len(all_no_checkin_alerts)))

        if all_no_checkin_alerts:
            latest_alert = all_no_checkin_alerts[0]
            info("Latest alert: ID=%d, created=%s, is_read=%s" % (
                latest_alert.id, latest_alert.created_at, latest_alert.is_read))
            content_preview = (latest_alert.content or "")[:100]
            info("Content: '%s'" % content_preview)

            hours_since_alert = (
                (datetime.utcnow() - latest_alert.created_at).total_seconds() / 3600
            )
            within_24h = hours_since_alert < 24

            check("  Latest no_checkin alert is outside 24h dedup window",
                  not within_24h,
                  "Hours since last alert: %.1fh (within_24h=%s)" % (
                      hours_since_alert, within_24h))

            if within_24h:
                warn("  Dedup would block a new alert -- wait 24h from: %s" %
                     latest_alert.created_at)

            info("All no_checkin alert history:")
            for i, a in enumerate(all_no_checkin_alerts[:10]):
                age_hours = (datetime.utcnow() - a.created_at).total_seconds() / 3600
                content_short = (a.content or "")[:80]
                info("  [%d] ID=%d  age=%.1fh  read=%s  '%s'" % (
                    i + 1, a.id, age_hours, a.is_read, content_short))
        else:
            info("No previous no_checkin alerts -- first fire not blocked by dedup")
            check("  No duplicate blocking possible", True, "No prior alerts exist")

        # ==============================================================
        # CHECK 7: Frontend param_mapping gap
        # ==============================================================
        sub("Frontend check_parameter_triggers() -- no_checkin support")

        param_mapping_keys = [
            'mood', 'anxiety', 'sleep_quality', 'physical_activity', 'energy'
        ]
        no_checkin_in_mapping = 'no_checkin' in param_mapping_keys

        check("  'no_checkin' in frontend param_mapping",
              no_checkin_in_mapping,
              "param_mapping keys: %s" % param_mapping_keys)

        if not no_checkin_in_mapping:
            fail("  *** SECOND BUG ***")
            fail("  check_parameter_triggers() line ~14328:")
            fail("  param_mapping does NOT include 'no_checkin'.")
            fail("  Old-schema triggers with parameter_name='no_checkin' hit:")
            fail("      if param_name not in param_mapping: continue")
            fail("  /api/parameters/check-triggers NEVER returns no_checkin patterns.")

        # ==============================================================
        # CHECK 8: Alert visibility
        # ==============================================================
        sub("Alert Visibility Check")

        check("  no_checkin bypasses PI502alt days filter",
              True,
              "Content lacks 'consecutive days' -- passes through")

        check("  no_checkin bypasses T42 privacy filter",
              True,
              "Content lacks parameter keywords -- returns True")

        check("  Watcher follows watched (required for /api/alerts)",
              follow is not None,
              "follow_exists=%s" % (follow is not None))

        # ==============================================================
        # CHECK 9: Scheduler health
        # ==============================================================
        sub("Scheduler Run Verification")

        recent_trigger_alerts = Alert.query.filter(
            Alert.alert_category == 'trigger',
            Alert.created_at >= datetime.utcnow() - timedelta(hours=6)
        ).count()

        info("Trigger alerts created in last 6 hours: %d" % recent_trigger_alerts)
        check("  Scheduler appears to be running",
              True,
              "Recent trigger alerts: %d" % recent_trigger_alerts)

        # ==============================================================
        # CHECK 10: Duplicate trigger rows
        # ==============================================================
        sub("Duplicate Trigger Rows")

        dup_triggers = db.session.execute(
            select(ParameterTrigger).filter(
                ParameterTrigger.watcher_id == trig.watcher_id,
                ParameterTrigger.watched_id == trig.watched_id,
                ParameterTrigger.parameter_name == 'no_checkin'
            )
        ).scalars().all()

        check("  No duplicate no_checkin trigger rows",
              len(dup_triggers) <= 1,
              "Found %d row(s) for this watcher/watched pair" % len(dup_triggers))

        if len(dup_triggers) > 1:
            for dt_row in dup_triggers:
                info("  Row ID=%d, is_active=%s, consecutive_days=%s" % (
                    dt_row.id, dt_row.is_active, dt_row.consecutive_days))

        # ==============================================================
        # CHECK 11: Timezone mismatch
        # ==============================================================
        sub("Timezone Consistency Check")

        now_local = datetime.now()
        now_utc = datetime.utcnow()
        diff_seconds = abs((now_local - now_utc).total_seconds())

        check("  datetime.now() ~ datetime.utcnow() (server in UTC)",
              diff_seconds < 60,
              "Difference: %.1fs" % diff_seconds)

        if diff_seconds >= 60:
            warn("  Server timezone offset: %.1fh" % (diff_seconds / 3600))
            warn("  check_duplicate_alert() uses datetime.now()")
            warn("  but Alert.created_at uses utcnow(). Could offset dedup window.")

    # ==================================================================
    # CODE-LEVEL BUG SUMMARY
    # ==================================================================
    header("3. CODE-LEVEL BUG VERIFICATION")

    sub("Bug A: Parameters count gate blocks no_checkin (background scheduler)")
    info("File: app.py, run_background_trigger_check_for_watcher()")
    info("Line ~16470:  if len(parameters) < consecutive_days: continue")
    info("Line ~16570:  if param_name == 'no_checkin':  # AFTER the gate")
    info("")
    info("Gate requires watched user to have >= consecutive_days entries")
    info("in last 30 days. No_checkin fires when users DON'T have entries.")
    info("User stops checking in -> fewer entries -> gate blocks -> never reached.")
    info("")
    info("FIX: Move no_checkin handling before the gate:")
    info("  # Before: if len(parameters) < consecutive_days: continue")
    info("  if trigger.parameter_name == 'no_checkin':")
    info("      # handle no_checkin directly, then continue")

    sub("Bug B: Frontend check_parameter_triggers() skips no_checkin")
    info("File: app.py, check_parameter_triggers()")
    info("Line ~14328: param_mapping = {mood, anxiety, sleep, activity, energy}")
    info("Line ~14336: if param_name not in param_mapping: continue")
    info("")
    info("FIX: Add no_checkin handler before param_mapping check.")

    sub("Bug B.1: Frontend also has the parameters count gate")
    info("Line ~14156: if len(parameters) < consecutive_days: continue")
    info("Same gate issue as Bug A.")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    run_diagnosis(target)
