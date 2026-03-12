"""
Vercel Serverless Function — /api/new_game
初始化新游戏，返回开局信息与初始状态。
"""
import json
import sys
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# 将项目根目录加入 sys.path，以便导入 storyweaver 等模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from storyweaver.schemas import get_initial_state

SCENARIOS_DIR = PROJECT_ROOT / "data" / "scenarios"

# CORS 响应头
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            scenario_name = "act1_huazhou"

            # 支持通过请求体指定场景
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                body = json.loads(self.rfile.read(content_length))
                scenario_name = body.get("scenario", scenario_name)

            scenario_path = SCENARIOS_DIR / f"{scenario_name}.json"
            if not scenario_path.exists():
                self._json_error(404, f"Scenario not found: {scenario_name}")
                return

            with open(scenario_path, encoding="utf-8") as f:
                scenario = json.load(f)

            state = get_initial_state(scenario)

            result = {
                "narration":          state["narration"],
                "dialogue":           state["dialogue"],
                "backstory_fragment": state["backstory_fragment"],
                "next_choices":       state["next_choices"],
                "state_delta":        {},
                "agent_logs":         ["[API] New game started"],
                "latency_ms":         0.0,
                "consistency_passed": True,
                "repair_suggestion":  "",
            }

            self._json_response(200, {"result": result, "state": dict(state)})

        except Exception as e:
            self._json_error(500, str(e))

    # ── 工具方法 ──────────────────────────────────────────────────────
    def _json_response(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status: int, message: str):
        self._json_response(status, {"error": message})
