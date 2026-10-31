#!/usr/bin/env bash
# Regression check for the game (worldbox/) and Arthur (arthur/), in one go:
#   1. md5 of the reference headless run (--no-ai, seed 42, 3000 days, no keys
#      in the environment) against the value in docs/worldbox/05-executar-e-testar.md;
#   2. every offline test in tests/worldbox/ and tests/arthur/ (fake APIs, no
#      network, the real .env is never read).
# Run from anywhere:  tools/regress.sh        (only one part: --md5 | --tests)
# Exit code 0 only when everything passed. Takes a few minutes.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
EXPECTED_MD5="46183c8d284315695c7706c0f923745a"
KEYS=(-u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u LLM_BASE_URL -u LLM_MODEL -u LLM_API_KEY)
export PYTHONDONTWRITEBYTECODE=1

[ -x "$PY" ] || { echo "No .venv at $ROOT/.venv (see docs/ambiente.md)"; exit 2; }
want_md5=1; want_tests=1
case "${1:-}" in
  --md5) want_tests=0 ;;
  --tests) want_md5=0 ;;
  "") ;;
  *) echo "usage: tools/regress.sh [--md5|--tests]"; exit 2 ;;
esac

failed=()
md5_of() { if command -v md5 >/dev/null; then md5 -q; else md5sum | cut -d' ' -f1; fi; }

if [ "$want_md5" = 1 ]; then
  echo "== md5: worldbox --no-ai --days 3000 --seed 42"
  got=$(cd "$ROOT/worldbox" && env "${KEYS[@]}" "$PY" -m worldbox.main --no-ai --days 3000 --seed 42 | md5_of)
  if [ "$got" = "$EXPECTED_MD5" ]; then
    echo "PASS md5 $got"
  else
    echo "FAIL md5 $got (expected $EXPECTED_MD5)"; failed+=("md5")
  fi
fi

if [ "$want_tests" = 1 ]; then
  for suite in worldbox arthur; do
    for t in "$ROOT"/tests/"$suite"/test_*.py; do
      name="$suite/$(basename "$t")"
      out=$(cd "$ROOT" && "$PY" -I -B "$t" "$ROOT/$suite" 2>&1)
      if [ $? -eq 0 ]; then
        echo "PASS $name"
      else
        echo "FAIL $name"; echo "$out" | grep -E "^FAIL|Error|Traceback" | head -5 | sed 's/^/    /'
        failed+=("$name")
      fi
    done
  done
fi

echo
if [ ${#failed[@]} -eq 0 ]; then
  echo "REGRESSION: all passed"
else
  echo "REGRESSION: ${#failed[@]} failed: ${failed[*]}"; exit 1
fi
