#!/usr/bin/env python3
"""
ChatGPT Proxy for Trapdoor

Run this locally to create a bridge between ChatGPT and your Trapdoor instance.

Usage:
    python3 chatgpt_proxy.py

Then tell ChatGPT to access:
    http://localhost:5000/chat
    http://localhost:5000/ls
    http://localhost:5000/read
    http://localhost:5000/write
    http://localhost:5000/exec

Or upload chatgpt_proxy_client.py to ChatGPT for easy access.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import sys
from pathlib import Path

# Add Trapdoor directory to path
sys.path.insert(0, str(Path(__file__).parent))
import trapdoor_connector as td

app = Flask(__name__)
CORS(app)  # Allow requests from any origin

@app.route('/health', methods=['GET'])
def health():
    """Check if proxy and Trapdoor are reachable"""
    try:
        trapdoor_health = td.health()
        return jsonify({
            "proxy": "ok",
            "trapdoor": trapdoor_health
        })
    except Exception as e:
        return jsonify({
            "proxy": "ok",
            "trapdoor": "error",
            "error": str(e)
        }), 503


@app.route('/chat', methods=['POST'])
def chat():
    """
    Chat with local model

    Body: {"prompt": "your message"}
    Returns: {"response": "model response"}
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({"error": "Missing 'prompt' field"}), 400

        response = td.chat(prompt)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/ls', methods=['GET'])
def list_files():
    """
    List directory contents

    Query: ?path=/path/to/dir
    Returns: {"files": [...]}
    """
    try:
        path = request.args.get('path', '/')
        files = td.ls(path)
        return jsonify({"files": files, "path": path})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/read', methods=['GET', 'POST'])
def read_file():
    """
    Read file contents

    Query: ?path=/path/to/file
    OR Body: {"path": "/path/to/file"}
    Returns: {"content": "file contents", "path": "..."}
    """
    try:
        if request.method == 'POST':
            data = request.get_json()
            path = data.get('path', '')
        else:
            path = request.args.get('path', '')

        if not path:
            return jsonify({"error": "Missing 'path' parameter"}), 400

        content = td.read_file(path)
        return jsonify({"content": content, "path": path})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/write', methods=['POST'])
def write_file():
    """
    Write file contents

    Body: {"path": "/path/to/file", "content": "file contents"}
    Returns: {"status": "ok", "path": "..."}
    """
    try:
        data = request.get_json()
        path = data.get('path', '')
        content = data.get('content', '')

        if not path:
            return jsonify({"error": "Missing 'path' field"}), 400

        result = td.write_file(path, content)
        return jsonify({"status": "ok", "path": path, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/exec', methods=['POST'])
def execute():
    """
    Execute command

    Body: {"cmd": ["ls", "-la"], "cwd": "/tmp"}
    Returns: {"stdout": "...", "stderr": "...", "returncode": 0}
    """
    try:
        data = request.get_json()
        cmd = data.get('cmd', [])
        cwd = data.get('cwd', '/tmp')

        if not cmd:
            return jsonify({"error": "Missing 'cmd' field"}), 400

        result = td.exec_command(cmd, cwd=cwd)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/mkdir', methods=['POST'])
def make_dir():
    """
    Create directory

    Body: {"path": "/path/to/dir"}
    Returns: {"status": "ok", "path": "..."}
    """
    try:
        data = request.get_json()
        path = data.get('path', '')

        if not path:
            return jsonify({"error": "Missing 'path' field"}), 400

        result = td.mkdir(path)
        return jsonify({"status": "ok", "path": path, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/rm', methods=['POST'])
def remove():
    """
    Remove file or directory

    Body: {"path": "/path/to/remove"}
    Returns: {"status": "ok", "path": "..."}
    """
    try:
        data = request.get_json()
        path = data.get('path', '')

        if not path:
            return jsonify({"error": "Missing 'path' field"}), 400

        result = td.rm(path)
        return jsonify({"status": "ok", "path": path, "result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ChatGPT Proxy for Trapdoor")
    print("=" * 60)
    print()
    print("Testing Trapdoor connection...")

    if td.test_connection():
        print()
        print("✅ Proxy ready!")
        print()
        print("Upload chatgpt_proxy_client.py to ChatGPT, then:")
        print()
        print("  import chatgpt_proxy_client as proxy")
        print("  proxy.chat('Hello!')")
        print("  proxy.ls('/Users/patricksomerville/Desktop')")
        print()
        print("=" * 60)
        print()

        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        print()
        print("❌ Cannot connect to Trapdoor")
        print("Make sure Trapdoor is running first!")
        sys.exit(1)
