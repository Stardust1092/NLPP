"""
Vercel Serverless Function — /api/step
接收玩家输入与当前游戏状态，运行 LangGraph Pipeline，返回结果与更新后的状态。
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from storyweaver.graph import get_graph

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
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._json_error(400, "Request body is required")
                return

            body = json.loads(self.rfile.read(content_length))

            player_input = body.get("player_input", "")
            state = body.get("state")

            if not player_input:
                self._json_error(400, "player_input is required")
                return
            if state is None:
                self._json_error(400, "state is required (call /api/new_game first)")
                return

            # 更新状态
            state["player_input"] = player_input
            state["turn_id"] = state.get("turn_id", 0) + 1

            # 运行 LangGraph Pipeline
            graph = get_graph()
            t0 = time.time()
            result_state = graph.invoke(state)
            elapsed = (time.time() - t0) * 1000

            result = {
                "narration":          result_state.get("narration", ""),
                "dialogue":           result_state.get("dialogue", {}),
                "backstory_fragment": result_state.get("backstory_fragment", ""),
                "next_choices":       result_state.get("next_choices", []),
                "state_delta":        result_state.get("state_delta", {}),
                "agent_logs":         result_state.get("agent_logs", []),
                "latency_ms":         elapsed,
                "consistency_passed": result_state.get("consistency_passed", True),
                "repair_suggestion":  result_state.get("repair_suggestion", ""),
            }

            self._json_response(200, {"result": result, "state": dict(result_state)})

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
