#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
VERIFY_CODE="${VERIFY_CODE:-123456}"
PASSWORD="${PASSWORD:-ChangeMe123!}"
ALICE_EMAIL="${ALICE_EMAIL:-alice@campus.local}"
BOB_EMAIL="${BOB_EMAIL:-bob@campus.local}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@campus.local}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

extract_json_field() {
  local file="$1"
  local key="$2"
  python3 - "$file" "$key" <<'PY'
import json, sys
file = sys.argv[1]
key = sys.argv[2]
with open(file, "r", encoding="utf-8") as f:
    data = json.load(f)

def pick(root, path):
    cur = root
    for p in path:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur

paths = {
    "token": [["data", "token"], ["token"]],
    "user_id": [["data", "user", "id"], ["user", "id"]],
}
for p in paths.get(key, []):
    val = pick(data, p)
    if val is not None:
        print(val)
        break
PY
}

login_and_get_token() {
  local email="$1"
  local out="$2"
  curl -sS -X POST "${BASE_URL}/api/v1/auth/email/verify" \
    -H "Content-Type: application/json" \
    -d "{\"campus_email\":\"${email}\",\"code\":\"${VERIFY_CODE}\",\"password\":\"${PASSWORD}\"}" > "${out}"
}

assert_api_ok() {
  local file="$1"
  local label="$2"
  if ! python3 - "$file" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
code = data.get('code')
sys.exit(0 if code == 0 else 1)
PY
  then
    echo "接口失败：${label}"
    cat "${file}"
    exit 1
  fi
}

echo "==> 1) 登录 Alice"
alice_resp="${tmpdir}/alice_login.json"
login_and_get_token "${ALICE_EMAIL}" "${alice_resp}"
assert_api_ok "${alice_resp}" "Alice 登录"
ALICE_TOKEN="$(extract_json_field "${alice_resp}" token)"
if [[ -z "${ALICE_TOKEN}" ]]; then
  echo "Alice 登录失败：未获取到 token"
  cat "${alice_resp}"
  exit 1
fi

echo "==> 2) 登录 Bob"
bob_resp="${tmpdir}/bob_login.json"
login_and_get_token "${BOB_EMAIL}" "${bob_resp}"
assert_api_ok "${bob_resp}" "Bob 登录"
BOB_TOKEN="$(extract_json_field "${bob_resp}" token)"
if [[ -z "${BOB_TOKEN}" ]]; then
  echo "Bob 登录失败：未获取到 token"
  cat "${bob_resp}"
  exit 1
fi

echo "==> 3) 登录 Admin"
admin_resp="${tmpdir}/admin_login.json"
login_and_get_token "${ADMIN_EMAIL}" "${admin_resp}"
assert_api_ok "${admin_resp}" "Admin 登录"
ADMIN_TOKEN="$(extract_json_field "${admin_resp}" token)"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Admin 登录失败：未获取到 token"
  cat "${admin_resp}"
  exit 1
fi

echo "==> 4) 拉取任务列表并提取联调任务ID"
tasks_json="${tmpdir}/tasks.json"
curl -sS "${BASE_URL}/api/v1/tasks?page=1&page_size=100" \
  -H "Authorization: Bearer ${ALICE_TOKEN}" > "${tasks_json}"
assert_api_ok "${tasks_json}" "任务列表"

TASK_DONE_ID="$(python3 - "${tasks_json}" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
items=data.get("data",{}).get("list",[])
for item in items:
    if item.get("title")=="联调任务-09-已完成":
        print(item.get("id"))
        break
PY
)"
TASK_DISPUTED_ID="$(python3 - "${tasks_json}" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
items=data.get("data",{}).get("list",[])
for item in items:
    if item.get("title")=="联调任务-10-申诉中":
        print(item.get("id"))
        break
PY
)"

if [[ -z "${TASK_DONE_ID}" || -z "${TASK_DISPUTED_ID}" ]]; then
  echo "未找到联调任务ID，请先执行 mock data 脚本。"
  cat "${tasks_json}"
  exit 1
fi

echo "==> 5) 任务详情与状态日志"
curl -sS "${BASE_URL}/api/v1/tasks/${TASK_DONE_ID}" \
  -H "Authorization: Bearer ${ALICE_TOKEN}" > "${tmpdir}/task_detail.json"
assert_api_ok "${tmpdir}/task_detail.json" "任务详情"
curl -sS "${BASE_URL}/api/v1/tasks/${TASK_DONE_ID}/status-logs" \
  -H "Authorization: Bearer ${ALICE_TOKEN}" > "${tmpdir}/task_logs.json"
assert_api_ok "${tmpdir}/task_logs.json" "任务状态日志"

echo "==> 6) 获取任务聊天会话并拉取消息"
chat_json="${tmpdir}/chat.json"
curl -sS "${BASE_URL}/api/v1/tasks/${TASK_DISPUTED_ID}/chat" \
  -H "Authorization: Bearer ${BOB_TOKEN}" > "${chat_json}"
assert_api_ok "${chat_json}" "任务聊天会话"
CHAT_ID="$(python3 - "${chat_json}" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
chat_id=data.get("data",{}).get("chat_id") or data.get("data",{}).get("id")
if chat_id is not None:
    print(chat_id)
PY
)"
if [[ -n "${CHAT_ID}" ]]; then
  curl -sS "${BASE_URL}/api/v1/chats/${CHAT_ID}/messages?cursor=0&page_size=20" \
    -H "Authorization: Bearer ${BOB_TOKEN}" > "${tmpdir}/chat_messages.json"
  assert_api_ok "${tmpdir}/chat_messages.json" "聊天消息列表"

  echo "==> 7) 查询聊天未读并标记已读"
  curl -sS "${BASE_URL}/api/v1/me/chats/unread" \
    -H "Authorization: Bearer ${BOB_TOKEN}" > "${tmpdir}/chat_unread_before.json"
  assert_api_ok "${tmpdir}/chat_unread_before.json" "聊天未读统计(已读前)"
  curl -sS -X POST "${BASE_URL}/api/v1/chats/${CHAT_ID}/read" \
    -H "Authorization: Bearer ${BOB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}' > "${tmpdir}/chat_mark_read.json"
  assert_api_ok "${tmpdir}/chat_mark_read.json" "标记聊天已读"
  curl -sS "${BASE_URL}/api/v1/me/chats/unread" \
    -H "Authorization: Bearer ${BOB_TOKEN}" > "${tmpdir}/chat_unread_after.json"
  assert_api_ok "${tmpdir}/chat_unread_after.json" "聊天未读统计(已读后)"
fi

echo "==> 8) 查询我的举报"
curl -sS "${BASE_URL}/api/v1/reports/mine?page=1&page_size=20" \
  -H "Authorization: Bearer ${BOB_TOKEN}" > "${tmpdir}/my_reports.json"
assert_api_ok "${tmpdir}/my_reports.json" "我的举报"

echo "==> 9) 管理端查询待处理举报"
curl -sS "${BASE_URL}/api/v1/admin/reports?status=PENDING&page=1&page_size=20" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" > "${tmpdir}/admin_reports.json"
assert_api_ok "${tmpdir}/admin_reports.json" "管理端举报列表"

echo "==> 冒烟完成"
echo "任务ID: DONE=${TASK_DONE_ID}, DISPUTED=${TASK_DISPUTED_ID}, CHAT=${CHAT_ID:-N/A}"
