"""Exercise the real memd stdio binary with an isolated synthetic vault."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


with tempfile.TemporaryDirectory(prefix="forja-memory-mcp-") as temp:
    env = dict(os.environ, HOME=temp, XDG_DATA_HOME=f"{temp}/data", XDG_CONFIG_HOME=f"{temp}/config")
    process = subprocess.Popen([sys.argv[1], "--mcp"], env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def request(number, method, params=None):
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": number, "method": method,
                                        "params": params or {}}) + "\n")
        process.stdin.flush()
        reply = json.loads(process.stdout.readline())
        assert reply["id"] == number, reply
        return reply["result"]

    def call(number, name, arguments):
        result = request(number, "tools/call", {"name": f"memory_{name}", "arguments": arguments})
        assert not result.get("isError"), result
        return json.loads(result["content"][0]["text"])

    try:
        assert request(1, "initialize")["serverInfo"]["name"] == "hero-memory"
        assert len(request(2, "tools/list")["tools"]) == 5
        saved = call(3, "remember", {"note": "Decisão game-api: manter API local"})["path"]
        assert call(4, "search", {"query": "game"})[0]["path"] == saved
        links = request(40, "tools/call", {"name": "memory_search", "arguments": {"query": "game"}})["content"]
        assert links[1]["type"] == "resource_link" and links[1]["uri"].startswith("file:///"), links
        assert call(5, "timeline", {"days": 1})[0]["path"] == saved
        (Path(temp) / "ForjaOS/vault/graph/graph.json").write_text(json.dumps({
            "nodes": [{"id": saved, "label": "game-api"}],
            "links": [{"source": saved, "target": "repo:game-api"}]}))
        assert len(call(6, "related", {"entity": "game-api"})) == 1
        assert call(7, "forget", {"id": saved})["forgotten"] == saved
        assert call(8, "search", {"query": "game"}) == []
        print("PASS: initialize, tools/list, remember, search, timeline, related, forget")
    finally:
        process.stdin.close()
        process.wait(timeout=10)
        assert process.returncode == 0
