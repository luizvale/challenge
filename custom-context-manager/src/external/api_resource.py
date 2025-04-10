"""
API resource implementation.

This module provides a concrete implementation of the Resource interface
for API connections and clients.
"""
import random
import time
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from ..core import Resource


class ApiResource(Resource):
    """
    Resource implementation for API connections.
    
    This class manages connections to external APIs,
    ensuring proper initialization and cleanup.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        name: Optional[str] = None,
    ):
        """
        Initialize an API resource.
        
        Args:
            base_url: Base URL of the API
            api_key: Optional API key for authentication
            headers: Optional default headers for requests
            timeout: Timeout for API requests in seconds
            retry_attempts: Number of retry attempts for failed requests
            retry_delay: Delay between retry attempts in seconds
            name: Optional custom name for the resource
        """
        self._base_url = base_url
        self._api_key = api_key
        self._headers = headers or {}
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._custom_name = name
        self._client = None
        self._logger = logging.getLogger(__name__)
        
        # Add API key to headers if provided
        if api_key:
            self._headers.setdefault("Authorization", f"Bearer {api_key}")
    
    @property
    def name(self) -> str:
        """
        Get the name of the resource.
        
        Returns:
            str: The custom name if provided, otherwise a name derived from the URL
        """
        if self._custom_name:
            return self._custom_name
            
        # Generate a name from the URL if no custom name is provided
        parsed_url = urlparse(self._base_url)
        host = parsed_url.netloc.split(':')[0]  # Remove port if present
        return f"API-{host}"
    
    def acquire(self) -> None:
        """
        Initialize the API client.
        
        This method sets up the API client and validates the connection
        by making a test request if applicable.
        
        Raises:
            ConnectionError: If the API client cannot be initialized or validated
        """
        if self._client is not None:
            self._logger.warning(f"API resource '{self.name}' already acquired")
            return
        
        try:
            self._logger.debug(f"Initializing API client for '{self.name}'")
            
            # For demonstration purposes, we'll create a simple client object
            # In a real application, this would use requests, aiohttp, or similar
            self._client = {
                "base_url": self._base_url,
                "headers": self._headers,
                "timeout": self._timeout,
                "initialized_at": time.time()
            }
            
            # Optional: make a test request to validate the connection
            # This is commented out as it's a mock implementation
            # self._test_connection()
            
            self._logger.info(f"API client for '{self.name}' initialized")
            
        except Exception as e:
            self._client = None
            self._logger.error(f"Failed to initialize API client for '{self.name}': {e}")
            raise ConnectionError(f"API client initialization failed: {e}")
    
    def release(self) -> None:
        """
        Release the API client.
        
        This method cleans up any resources used by the API client.
        
        Raises:
            RuntimeError: If there's an error cleaning up the client
        """
        if self._client is None:
            self._logger.warning(f"API resource '{self.name}' not acquired")
            return
        
        try:
            self._logger.debug(f"Releasing API client for '{self.name}'")
            
            # For a real HTTP client, we might close sessions or connections
            # For our mock client, we'll just set it to None
            self._client = None
            
            self._logger.info(f"API client for '{self.name}' released")
            
        except Exception as e:
            self._logger.error(f"Error releasing API client for '{self.name}': {e}")
            raise RuntimeError(f"Error releasing API client: {e}")
    
    @property
    def is_acquired(self) -> bool:
        """
        Check if the API client is acquired.
        
        Returns:
            bool: True if the client is acquired, False otherwise
        """
        return self._client is not None
    
    def _test_connection(self) -> None:
        """
        Test the API connection by making a simple request.
        
        Raises:
            ConnectionError: If the test request fails
        """
        # In a real implementation, this would make an actual request
        # For demonstration, we'll just simulate a test
        self._logger.debug(f"Testing API connection to '{self._base_url}'")
        
        # Simulate connection test
        if "invalid" in self._base_url.lower():
            raise ConnectionError(f"Test connection to {self._base_url} failed")

    def request(
            self,
            method: str,
            endpoint: str,
            data: Optional[Union[Dict[str, Any], List[Any]]] = None,
            params: Optional[Dict[str, str]] = None,
            headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Make a request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (will be appended to the base URL)
            data: Optional data to send with the request
            params: Optional query parameters
            headers: Optional headers to include with the request

        Returns:
            Any: Response object with json() method

        Raises:
            RuntimeError: If the client is not acquired
            ConnectionError: If the request fails
        """
        # Simulate network latency with more realistic patterns
        time.sleep(random.uniform(0.01, max(0.1, min(0.2, self._timeout * 0.05))))  # Scale with timeout

        # Fault injection for resilience testing
        if random.random() < 0.01:  # 1% chance of failure
            raise ConnectionError(f"Simulated network error for {method} {endpoint}")

        if self._client is None:
            raise RuntimeError(f"API client '{self.name}' not acquired")

        # Create a more sophisticated response object that has json() method
        try:
            self._logger.debug(f"Making {method} request to '{self.name}' endpoint '{endpoint}'")

            # Combine default headers with request-specific headers
            combined_headers = {**self._headers}
            if headers:
                combined_headers.update(headers)

            # Create a response object (not just a dict)
            response_data = {
                "status": 200,
                "method": method,
                "url": f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}",
                "data": data,
                "params": params,
                "headers": combined_headers,
                "timestamp": time.time()
            }

            # Error simulation
            if "error" in endpoint.lower():
                response_data["status"] = 400
                response_data["error"] = "Simulated error"
                raise ConnectionError(f"API request failed with status 400: Simulated error")

            # Create a response-like object with a json() method
            class ResponseObject:
                def __init__(self, data):
                    self.status = data["status"]
                    self.method = data["method"]
                    self.url = data["url"]
                    self._data = data

                def json(self):
                    """Return JSON representation of response data"""
                    if endpoint == "/users":
                        return [{"id": i, "name": f"User {i}"} for i in range(1, 11)]
                    elif endpoint == "/posts":
                        return [{"id": i, "title": f"Post {i}", "body": "Content"} for i in range(1, 6)]
                    elif endpoint == "/comments":
                        return [{"id": i, "postId": i % 5 + 1, "body": "Comment body"} for i in range(1, 16)]
                    elif endpoint == "/todos":
                        return [{"id": i, "title": f"Task {i}", "completed": i % 2 == 0} for i in range(1, 8)]
                    elif endpoint == "/albums":
                        return [{"id": i, "title": f"Album {i}"} for i in range(1, 4)]
                    else:
                        return {"result": "success", "data": []}

            return ResponseObject(response_data)

        except ConnectionError:
            # Let connection errors propagate
            raise
        except Exception as e:
            self._logger.error(f"API request to '{self.name}' failed: {e}")
            raise

    def get(self, endpoint: str, params: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Convenience method for making GET requests."""
        return self.request("GET", endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Any, **kwargs) -> Dict[str, Any]:
        """Convenience method for making POST requests."""
        return self.request("POST", endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Any, **kwargs) -> Dict[str, Any]:
        """Convenience method for making PUT requests."""
        return self.request("PUT", endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Convenience method for making DELETE requests."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource.
        
        Returns:
            Dict[str, Any]: A dictionary containing status information
        """
        status = super().get_status()
        status.update({
            "type": "api",
            "base_url": self._base_url,
            "has_api_key": bool(self._api_key),
            "timeout": self._timeout,
            "retry_attempts": self._retry_attempts
        })
        return status