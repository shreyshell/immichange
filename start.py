#!/usr/bin/env python3
"""
Combined startup script for Railway deployment.
Runs both the API server and AI processor.
"""

import subprocess
import sys
import os

def main():
    # Start AI processor in background
    print("🚀 Starting AI Processor in background...")
    ai_process = subprocess.Popen([sys.executable, 'ai_processor.py'])
    
    # Start API server in foreground
    print("🚀 Starting API Server...")
    os.system(f'{sys.executable} api_server.py')

if __name__ == "__main__":
    main()
