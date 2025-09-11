#!/usr/bin/env python3
"""
Minimal FastAPI wrapper for browser-use Agent

Provides:
- POST /run_task endpoint to execute browser automation tasks
- GET /health endpoint for health checks
"""

import asyncio
import base64
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from browser_use import Agent, ChatOpenAI
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession
from browser_use.llm.base import BaseChatModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Development mode configuration
DEV_MODE = os.getenv('DEV_MODE', '').lower() in ('true', '1', 'yes', 'on')
SCREENSHOTS_DIR = Path(tempfile.gettempdir()) / 'browser-use-screenshots'

if DEV_MODE:
	# Ensure screenshots directory exists in dev mode
	SCREENSHOTS_DIR.mkdir(exist_ok=True)
	logger.info(f"Development mode enabled - screenshots will be saved to: {SCREENSHOTS_DIR}")

app = FastAPI(
	title="Browser-Use API",
	description="API for browser automation using browser-use library",
	version="0.1.0",
)


class TaskRequest(BaseModel):
	"""Request model for running a browser automation task"""
	task: str
	model: str = "gpt-4.1-mini"
	max_steps: int = 100


class TaskResponse(BaseModel):
	"""Response model for completed task"""
	success: bool
	message: str
	steps_completed: int | None = None
	error: str | None = None
	result: str | None = None
	is_done: bool | None = None


class PreloadCaseRequest(BaseModel):
	"""Request model for preloading a Persona case"""
	case_token: str
	refresh_token: str

class PreloadCaseResponse(BaseModel):
	"""Response model for preloaded case"""
	success: bool
	message: str
	status_code: int | None = None
	screenshot: str | None = None  # Base64 encoded PNG screenshot
	error: str | None = None


@app.get("/health")
async def health_check():
	"""Health check endpoint"""
	return {"status": "healthy", "service": "browser-use-api"}


@app.post("/preload_case", response_model=PreloadCaseResponse)
async def preload_case(request: PreloadCaseRequest):
	"""Preload a Persona case by visiting the dashboard URL and returning the page body with status"""
	browser_session = None
	try:
		logger.info(f"Preloading case: {request.case_token}")
		
		case_url = f"https://app.withpersona.com/dashboard/cases/{request.case_token}?refresh-token={request.refresh_token}"
		
		# Create optimized browser profile
		profile = BrowserProfile(
			headless=True,
			chromium_sandbox=False,
			args=[
				'--single-process',
				'--headless=new',
				'--no-sandbox',
				'--disable-dev-shm-usage',
				'--disable-gpu',
				'--no-zygote',
				'--disable-extensions',
			]
		)
		
		browser_session = BrowserSession(browser_profile=profile)
		await browser_session.start()
		
		# Get CDP session
		cdp_session = await browser_session.get_or_create_cdp_session()
		
		# Track navigation response and pending requests
		navigation_response = {'status_code': None}
		pending_requests = set()
		session_active = True
		
		# Enable domains for comprehensive loading
		await cdp_session.cdp_client.send.Network.enable(session_id=cdp_session.session_id)
		await cdp_session.cdp_client.send.Page.enable(session_id=cdp_session.session_id)
		await cdp_session.cdp_client.send.Runtime.enable(session_id=cdp_session.session_id)
		
		# Enable fetch with request interception
		await cdp_session.cdp_client.send.Fetch.enable(
			params={'patterns': [{'urlPattern': '*'}]},
			session_id=cdp_session.session_id
		)
		
		# Handle network responses to capture status
		def on_response_received(event, session_id=None):
			response = event.get('response', {})
			if response.get('url') == case_url:
				navigation_response['status_code'] = response.get('status')
		
		# Register response handler
		cdp_session.cdp_client.register.Network.responseReceived(on_response_received)
		
		async def handle_request_paused(event, session_id=None):
			if not session_active:
				return
				
			request_id = event['requestId']
			headers = event.get('request', {}).get('headers', {})
			headers['Persona-Skip-Log-User-Action'] = 'true'
			
			try:
				await cdp_session.cdp_client.send.Fetch.continueRequest(
					params={
						'requestId': request_id,
						'headers': [{'name': k, 'value': v} for k, v in headers.items()]
					},
					session_id=cdp_session.session_id
				)
			except Exception as e:
				logger.debug(f"Failed to continue request {request_id}: {e}")
			finally:
				pending_requests.discard(request_id)
		
		def on_request_paused(event, session_id=None):
			if not session_active:
				return
			request_id = event['requestId']
			pending_requests.add(request_id)
			asyncio.create_task(handle_request_paused(event, session_id))
		
		cdp_session.cdp_client.register.Fetch.requestPaused(on_request_paused)
		
		# Navigate and wait for load
		await cdp_session.cdp_client.send.Page.navigate(
			params={'url': case_url},
			session_id=cdp_session.session_id
		)
		
		# Wait for page load and XHR completion
		await asyncio.sleep(3)  # Initial load
		
		# Wait for network idle (no pending requests for 500ms)
		for i in range(10):  # Max 5 seconds additional wait
			await asyncio.sleep(0.5)
			
			# Check if page is fully loaded
			try:
				result = await cdp_session.cdp_client.send.Runtime.evaluate(
					params={
						'expression': 'document.readyState === "complete" && window.performance.timing.loadEventEnd > 0'
					},
					session_id=cdp_session.session_id
				)
				
				if result.get('result', {}).get('value') is True and len(pending_requests) == 0:
					break
			except Exception as e:
				logger.debug(f"Error checking page state: {e}")
				break
		
		# Wait for any remaining pending requests to complete
		for _ in range(20):  # Max 2 more seconds
			if len(pending_requests) == 0:
				break
			await asyncio.sleep(0.1)
		
		# Take a screenshot of the final page
		screenshot_result = await cdp_session.cdp_client.send.Page.captureScreenshot(
			params={
				'format': 'png',
				'quality': 90,
				'fromSurface': True
			},
			session_id=cdp_session.session_id
		)
		
		# The screenshot is already base64 encoded
		screenshot_data = screenshot_result['data']
		status_code = navigation_response['status_code'] or 200
		
		# Save screenshot locally in development mode
		local_path = None
		if DEV_MODE:
			try:
				# Create filename with timestamp and case token
				timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
				filename = f"case_{request.case_token}_{timestamp}_{status_code}.png"
				local_path = SCREENSHOTS_DIR / filename
				
				# Decode base64 and save
				screenshot_bytes = base64.b64decode(screenshot_data)
				local_path.write_bytes(screenshot_bytes)
				
				logger.info(f"Screenshot saved to: {local_path}")
			except Exception as save_error:
				logger.warning(f"Failed to save screenshot locally: {save_error}")
		
		logger.info(f"Successfully preloaded case {request.case_token} with status {status_code}")
		
		return PreloadCaseResponse(
			success=True,
			message="Case preloaded successfully",
			status_code=status_code,
			screenshot=screenshot_data
		)
		
	except Exception as e:
		logger.error(f"Failed to preload case {request.case_token}: {str(e)}")
		return PreloadCaseResponse(
			success=False,
			message="Failed to preload case",
			status_code=None,
			error=str(e)
		)
	
	finally:
		# Mark session as inactive to prevent new request handling
		try:
			session_active = False
		except NameError:
			pass  # session_active wasn't defined yet
		
		if browser_session:
			try:
				# Give a moment for pending requests to complete
				await asyncio.sleep(0.2)
				await browser_session.stop()
			except Exception as cleanup_error:
				logger.warning(f"Error during cleanup: {cleanup_error}")


@app.post("/run_task", response_model=TaskResponse)
async def run_task(request: TaskRequest):
	"""Execute a browser automation task"""
	try:
		logger.info(f"Starting task: {request.task}")

		# Create LLM instance
		llm: BaseChatModel = ChatOpenAI(model=request.model)

		# Create production-optimized browser profile
		production_profile = BrowserProfile(
			headless=True,
			chromium_sandbox=False,
			args=[
				'--single-process',  # Critical for production containers
				"--headless=new",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-zygote",
        "--disable-extensions",
        "--enable-logging=stderr",
				"--v=1",
			]
		)

		# Create agent
		agent = Agent(
			task=request.task,
			llm=llm,
			browser_profile=production_profile,
		)

		# Run the task
		history = await agent.run(max_steps=request.max_steps)

		# Close the agent to clean up resources
		await agent.close()

		steps_count = len(history) if history else 0
		logger.info(f"Task completed successfully in {steps_count} steps: {request.task}")

		return TaskResponse(
			success=True,
			message="Task completed successfully",
			steps_completed=steps_count,
			result=history.final_result(),
			is_done=history.is_done()
		)

	except Exception as e:
		logger.error(f"Task failed: {str(e)}")

		# Try to clean up agent if it exists
		try:
			if 'agent' in locals():
				await agent.close()
		except Exception:
			pass

		return TaskResponse(
			success=False,
			message="Task failed",
			steps_completed=0,
			error=str(e)
		)


if __name__ == "__main__":
	import uvicorn
	port = int(os.environ.get("PORT", "8080"))
	uvicorn.run(app, host="0.0.0.0", port=port)
