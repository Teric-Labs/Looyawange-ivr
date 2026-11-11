#!/usr/bin/env bash
# Simulate Africa's Talking Voice callbacks against a local IVR (no phone needed).
set -euo pipefail

BASE="${IVR_BASE:-http://127.0.0.1:8088}"
SID="smoke-$(date +%s)"
CALLER="+256700999888"

post() {
  local digits="${1:-}"
  local active="${2:-1}"
  curl -sS -X POST "$BASE/ivr/voice" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "isActive=${active}" \
    --data-urlencode "sessionId=${SID}" \
    --data-urlencode "callerNumber=${CALLER}" \
    --data-urlencode "dtmfDigits=${digits}" \
    --data-urlencode "recordingUrl="
}

echo "== Health =="
curl -sS "$BASE/health" | python3 -m json.tool | head -n 40
echo

echo "== 1) First ring → language picker =="
post "" | tee /tmp/ivr_step1.xml
echo
grep -q "GetDigits" /tmp/ivr_step1.xml
grep -qi "english\|press 1" /tmp/ivr_step1.xml

echo "== 2) Press 1 (English) → main menu =="
post "1" | tee /tmp/ivr_step2.xml
echo
grep -q "GetDigits" /tmp/ivr_step2.xml
grep -qi "complaint\|press 1" /tmp/ivr_step2.xml

echo "== 3) Press 8 → language picker again =="
post "8" | tee /tmp/ivr_step3.xml
echo
grep -qi "kiswahili\|oluganda\|english" /tmp/ivr_step3.xml

echo "== 4) Press 3 (Luganda) → Luganda menu =="
post "3" | tee /tmp/ivr_step4.xml
echo
grep -qi "oluganda\|nyiga\|lulondeddwa" /tmp/ivr_step4.xml

echo "== 5) Hang up =="
post "" "0" | tee /tmp/ivr_step5.xml
echo
grep -qi "ctdru\|goodbye\|weraba\|kwaheri" /tmp/ivr_step5.xml

echo
echo "OK — local language-gate smoke passed (session ${SID})"
