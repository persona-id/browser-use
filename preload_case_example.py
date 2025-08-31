#!/usr/bin/env python3
"""
Example of how to use the /preload_case endpoint
"""

import asyncio
import httpx


async def preload_persona_case(case_token: str, access_token: str, api_base_url: str = "http://localhost:8080"):
	"""
	Preload a Persona case by calling the /preload_case endpoint
	
	Args:
		case_token: The Persona case token (from the URL)
		access_token: Access token for Persona API authentication  
		api_base_url: Base URL of the browser-use API server
		
	Returns:
		dict: Response from the API containing success status and page body
	"""
	async with httpx.AsyncClient(timeout=30.0) as client:
		response = await client.post(
			f"{api_base_url}/preload_case",
			json={"case_token": case_token, "access_token": access_token}
		)
		
		return response.json()


# Example usage (commented out since it requires real credentials):
"""
async def main():
	# Example case token from a Persona dashboard URL like:
	# https://app.withpersona.com/dashboard/cases/cas_abc123def456
	case_token = "cas_abc123def456"
	
	# Your Persona access token
	access_token = "your_persona_access_token_here"
	
	try:
		result = await preload_persona_case(case_token, access_token)
		
		if result["success"]:
			print(f"✅ Successfully preloaded case {case_token}")
			print(f"Screenshot size: {len(result['screenshot'])} characters (base64)")
			# You can now decode and save the screenshot as needed
		else:
			print(f"❌ Failed to preload case: {result['error']}")
			
	except Exception as e:
		print(f"❌ Error calling API: {e}")


if __name__ == "__main__":
	asyncio.run(main())
"""

print("Example code for /preload_case endpoint created.")
print("To use this endpoint:")
print("1. Start the API server: python api_server.py")
print("2. Send POST request to /preload_case with case_token and access_token parameters")
print("3. The endpoint will visit the Persona URL with authentication and return a screenshot")