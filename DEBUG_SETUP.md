# VS Code Debugging Setup for Django on Docker

This guide explains how to debug your Django application running in Docker using VS Code.

## Prerequisites

- VS Code with Python extension installed
- Docker and Docker Compose
- VS Code Docker extension (recommended)

## Setup Overview

The debugging setup includes:
- `.vscode/launch.json` - Debug configurations
- `.vscode/settings.json` - Python interpreter and linting settings
- `.vscode/tasks.json` - Build and run tasks
- `docker-compose.debug.yml` - Docker compose file with debugging support
- Updated `Pipfile` with debugpy dependency

## How to Debug

### Method 1: Remote Attach (Recommended)

1. **Start the debug container:**
   ```bash
   docker-compose -f docker-compose.debug.yml up --build
   ```
   
   This will:
   - Build the container with debugpy installed
   - Start Django with debugpy listening on port 5678
   - Wait for a debugger to attach

2. **Attach VS Code debugger:**
   - Open VS Code in the project root
   - Go to Run and Debug (Ctrl+Shift+D)
   - Select "Python: Remote Attach (Docker)"
   - Click the play button or press F5

3. **Set breakpoints:**
   - Open any Python file in your Django app
   - Click in the gutter next to line numbers to set breakpoints

4. **Access your application:**
   - Open http://localhost:8000 in your browser
   - The debugger will pause at your breakpoints

### Method 2: Using VS Code Tasks

1. **Use Command Palette:**
   - Press Ctrl+Shift+P (Cmd+Shift+P on Mac)
   - Type "Tasks: Run Task"
   - Select "Docker: Build and Run (Debug)"

2. **Attach debugger:**
   - Once the container is running, use the "Python: Remote Attach (Docker)" configuration

## Available Configurations

### Launch Configurations
- **Python: Remote Attach (Docker)** - Attach to running Django container
- **Python: Django (Local)** - Run Django locally (if needed)

### Tasks
- **Docker: Build and Run (Debug)** - Start debug container
- **Docker: Stop Debug** - Stop debug container
- **Docker: Build (Production)** - Start production container

## Debugging Features

- **Breakpoints** - Pause execution at specific lines
- **Variable inspection** - View variable values in the debug panel
- **Call stack** - See the execution path
- **Debug console** - Execute Python code in the current context
- **Step through code** - Step over, into, and out of functions

## Troubleshooting

### Container won't start
- Check if ports 8000 and 5678 are available
- Ensure Docker is running
- Check container logs: `docker-compose -f docker-compose.debug.yml logs`

### Debugger won't attach
- Ensure the container is running and waiting for debugger
- Check that port 5678 is exposed and accessible
- Verify the debugpy is installed in the container

### Breakpoints not working
- Ensure you're using the correct Python interpreter
- Check that source code is mounted correctly in the container
- Verify file paths match between host and container

## File Structure

```
.
├── .vscode/
│   ├── launch.json          # Debug configurations
│   ├── settings.json        # VS Code settings
│   └── tasks.json           # Build tasks
├── app/
│   ├── Pipfile              # Updated with debugpy
│   └── ...
├── docker-compose.yml       # Production compose
├── docker-compose.debug.yml # Debug compose
└── DEBUG_SETUP.md          # This file
```

## Tips

1. **Use conditional breakpoints** - Right-click on breakpoints to add conditions
2. **Debug console** - Use the debug console to test expressions
3. **Environment variables** - Check `.env.dev` for environment configuration
4. **Hot reload** - Code changes are reflected immediately due to volume mounting
5. **Multiple services** - You can debug other services by adding debugpy to them

## Next Steps

- Set up debugging for Celery workers if needed
- Configure debugging for tests
- Add debugging for frontend JavaScript if applicable