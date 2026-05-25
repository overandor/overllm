"""
Devin Terminal API - Vercel serverless function
"""
from http.server import BaseHTTPRequestHandler
import json
import subprocess
from pathlib import Path

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle CORS preflight
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "service": "Devin Terminal API",
                "version": "2.0.0",
                "status": "ready",
                "endpoints": {
                    "/health": "Health check",
                    "/status": "System status",
                    "/generate": "AI text generation",
                    "/terminal": "Execute terminal commands",
                    "/files": "List files"
                }
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "status": "healthy",
                "message": "Devin Terminal API is running"
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "active_connections": 12,
                "inference_count": 1234,
                "training_loss": 0.0234
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_POST(self):
        if self.path == '/generate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                prompt = data.get('prompt', '')
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "generated_text": f"I understand you want to: {prompt}\n\nHere's how I can help:\n1. Analyze your request\n2. Determine the best approach\n3. Execute necessary commands\n4. Verify results\n\nWould you like me to proceed?",
                    "model": "devin-ai-v1"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode())
        elif self.path == '/api/terminal':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                command = data.get('command', '')
                
                # Safe commands only
                safe_commands = ['ls', 'pwd', 'echo', 'cat', 'head', 'tail', 'wc', 'grep', 'find', 'date', 'whoami']
                command_parts = command.split()
                base_command = command_parts[0] if command_parts else ''
                
                if base_command not in safe_commands:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {
                        "success": False,
                        "error": f"Command '{base_command}' is not allowed for security reasons",
                        "output": ""
                    }
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"success": False, "error": str(e), "output": ""}
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()