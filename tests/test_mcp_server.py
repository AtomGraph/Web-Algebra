"""The MCP servers, driven over the wire as a client would: newline-delimited
JSON-RPC on the stdio server's pipes (`web-algebra-mcp`), and the streamable
HTTP transport of `web_algebra.server:app` under uvicorn.

The messages are written by hand, not with the SDK's client, so the tests do
not change with the SDK they check.

- initialize answers with the server's name and the package's version;
- tools/list offers exactly the MCP tool operations, each with its own
  inputSchema;
- tools/call runs the operation and answers with its text;
- an operation's error is a tool result with isError, an unknown tool an
  error too.
"""

from __future__ import annotations

import json
import os
import select
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from importlib.metadata import version

import pytest

from web_algebra.mcp_tool import MCPTool
from web_algebra.operation import Operation

PROTOCOL = "2025-06-18"
INITIALIZE = {
    "protocolVersion": PROTOCOL,
    "capabilities": {},
    "clientInfo": {"name": "web-algebra-tests", "version": "0"},
}
ENV = {k: v for k, v in os.environ.items() if k not in ("CERT_PEM_PATH", "CERT_PASSWORD")}


def mcp_tools():
    return {cls.name(): cls for cls in Operation.list_operations() if issubclass(cls, MCPTool)}


# --- stdio


class Stdio:
    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "web_algebra"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=ENV,
            text=True,
        )
        self.next_id = 0

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None, timeout=30):
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.proc.stdout], [], [], deadline - time.monotonic())
            if not ready:
                break
            line = self.proc.stdout.readline()
            if not line:
                raise AssertionError("the server closed its output")
            answer = json.loads(line)
            if answer.get("id") == self.next_id:
                return answer
        raise AssertionError(f"no answer to {method}")

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture(scope="module")
def stdio():
    server = Stdio()
    answer = server.request("initialize", INITIALIZE, timeout=60)
    server.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    server.initialized = answer
    yield server
    server.close()


def test_initialize_names_the_server_and_its_version(stdio):
    info = stdio.initialized["result"]["serverInfo"]
    assert info["name"] == "web-algebra"
    assert info["version"] == version("web-algebra")


def test_initialize_offers_tools(stdio):
    assert "tools" in stdio.initialized["result"]["capabilities"]


def test_the_tools_are_the_mcp_operations(stdio):
    tools = stdio.request("tools/list")["result"]["tools"]
    expected = mcp_tools()
    assert sorted(t["name"] for t in tools) == sorted(expected)
    for tool in tools:
        cls = expected[tool["name"]]
        assert tool["description"] == cls.description()
        assert tool["inputSchema"] == cls.inputSchema()


def test_a_call_answers_with_the_operations_text(stdio):
    result = stdio.request("tools/call", {"name": "ResolveURI", "arguments": {"base": "http://example.org/a/b", "relative": "c"}})["result"]
    assert not result.get("isError")
    assert [c["text"] for c in result["content"] if c["type"] == "text"] == ["http://example.org/a/c"]


def test_each_now_call_is_its_own_evaluation(stdio):
    # formal-semantics.md §4.2 NOW: two MCP tool calls each have their own time
    first, second = (
        stdio.request("tools/call", {"name": "NOW", "arguments": {}})["result"]["content"][0]["text"]
        for _ in range(2)
    )
    assert datetime.fromisoformat(first).utcoffset() is not None
    assert datetime.fromisoformat(second) > datetime.fromisoformat(first)


def test_a_string_call(stdio):
    result = stdio.request("tools/call", {"name": "EncodeForURI", "arguments": {"input": "a b/c"}})["result"]
    assert [c["text"] for c in result["content"]] == ["a%20b%2Fc"]


def test_an_operation_error_is_a_tool_error(stdio):
    answer = stdio.request("tools/call", {"name": "Replace", "arguments": {"input": "abc", "pattern": "(", "replacement": "x"}})
    assert answer.get("result", {}).get("isError") is True


def test_an_unknown_tool_is_an_error(stdio):
    answer = stdio.request("tools/call", {"name": "NoSuchTool", "arguments": {}})
    assert "error" in answer or answer["result"].get("isError") is True


# --- streamable HTTP


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def http():
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "web_algebra.server:app", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=ENV,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("the HTTP server did not start")
    yield f"http://127.0.0.1:{port}/mcp"
    proc.terminate()
    proc.wait(timeout=10)


def post(url, message, session=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL}
    if session:
        headers["Mcp-Session-Id"] = session
    request = urllib.request.Request(url, data=json.dumps(message).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
        session = response.headers.get("Mcp-Session-Id", session)
        if response.headers.get_content_type() == "text/event-stream":
            answers = [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:") and line[5:].strip()]
        else:
            answers = [json.loads(body)] if body.strip() else []
    return [a for a in answers if a.get("id") == message.get("id")], session


def test_http_initialize_and_call(http):
    (answer,), session = post(http, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": INITIALIZE})
    assert answer["result"]["serverInfo"]["name"] == "web-algebra"
    post(http, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    (answer,), _ = post(http, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "ResolveURI", "arguments": {"base": "http://example.org/a/b", "relative": "../c"}}}, session)
    assert [c["text"] for c in answer["result"]["content"]] == ["http://example.org/c"]
