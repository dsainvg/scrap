"""
API Key Manager for rotating multiple NVIDIA API keys to increase rate limits.
"""

import os
import logging
import threading
from typing import List, Optional
from collections import deque
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manages multiple NVIDIA API keys with round-robin rotation.
    Increases effective rate limits by distributing requests across multiple keys.
    """
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        Initialize the API key manager.
        
        Args:
            api_keys: List of NVIDIA API keys. If None, loads from environment variables.
        """
        self.api_keys = api_keys or self._load_api_keys()
        
        if not self.api_keys:
            raise ValueError(
                "No NVIDIA API keys found. Set NVIDIA_API_KEY or NVIDIA_API_KEY_1, "
                "NVIDIA_API_KEY_2, etc. in your .env file."
            )
        
        # Use deque for efficient rotation
        self.key_queue = deque(self.api_keys)
        self.lock = threading.Lock()
        
        # Track usage statistics
        self.usage_stats = {key: 0 for key in self.api_keys}
        self.error_counts = {key: 0 for key in self.api_keys}
        
        logger.info(f"Initialized API Key Manager with {len(self.api_keys)} key(s)")
    
    def _load_api_keys(self) -> List[str]:
        """
        Load API keys from environment variables.
        Supports:
        - NVIDIA_API_KEY (single key)
        - NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, ... (multiple keys)
        - NVIDIA_API_KEYS (comma-separated list)
        """
        keys = []
        
        # Check for comma-separated list
        keys_str = os.getenv('NVIDIA_API_KEYS')
        if keys_str:
            keys = [k.strip() for k in keys_str.split(',') if k.strip()]
            logger.info(f"Loaded {len(keys)} API keys from NVIDIA_API_KEYS")
            return keys
        
        # Check for single key
        single_key = os.getenv('NVIDIA_API_KEY')
        if single_key:
            keys.append(single_key)
        
        # Check for numbered keys (NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, etc.)
        index = 1
        while True:
            key = os.getenv(f'NVIDIA_API_KEY_{index}')
            if not key:
                break
            keys.append(key)
            index += 1
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for key in keys:
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
        
        if unique_keys:
            logger.info(f"Loaded {len(unique_keys)} unique API key(s) from environment")
        
        return unique_keys
    
    def get_next_key(self) -> str:
        """
        Get the next API key using round-robin rotation.
        Thread-safe.
        
        Returns:
            API key string
        """
        with self.lock:
            # Rotate the queue
            self.key_queue.rotate(-1)
            key = self.key_queue[0]
            
            # Update usage stats
            self.usage_stats[key] += 1
            
            return key
    
    def report_error(self, api_key: str):
        """
        Report an error for a specific API key.
        Used for tracking problematic keys.
        
        Args:
            api_key: The API key that encountered an error
        """
        with self.lock:
            if api_key in self.error_counts:
                self.error_counts[api_key] += 1
                logger.warning(f"Error reported for API key ending in ...{api_key[-6:]}")
    
    def report_success(self, api_key: str):
        """
        Report successful usage of an API key.
        Resets error count for the key.
        
        Args:
            api_key: The API key that was used successfully
        """
        with self.lock:
            if api_key in self.error_counts:
                self.error_counts[api_key] = 0
    
    def get_stats(self) -> dict:
        """
        Get usage statistics for all API keys.
        
        Returns:
            Dictionary with usage stats
        """
        with self.lock:
            total_requests = sum(self.usage_stats.values())
            total_errors = sum(self.error_counts.values())
            
            return {
                'total_keys': len(self.api_keys),
                'total_requests': total_requests,
                'total_errors': total_errors,
                'usage_per_key': {
                    f"Key ...{key[-6:]}": {
                        'requests': self.usage_stats[key],
                        'errors': self.error_counts[key]
                    }
                    for key in self.api_keys
                },
                'error_rate': total_errors / total_requests if total_requests > 0 else 0
            }
    
    def print_stats(self):
        """Print usage statistics in a readable format"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("API KEY USAGE STATISTICS")
        print("="*60)
        print(f"Total Keys: {stats['total_keys']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Total Errors: {stats['total_errors']}")
        print(f"Error Rate: {stats['error_rate']:.2%}")
        print("\nPer-Key Statistics:")
        
        for key_name, key_stats in stats['usage_per_key'].items():
            print(f"  {key_name}:")
            print(f"    Requests: {key_stats['requests']}")
            print(f"    Errors: {key_stats['errors']}")
        
        print("="*60 + "\n")
    
    def remove_key(self, api_key: str):
        """
        Remove a problematic API key from rotation.
        
        Args:
            api_key: The API key to remove
        """
        with self.lock:
            if api_key in self.api_keys:
                self.api_keys.remove(api_key)
                self.key_queue = deque([k for k in self.key_queue if k != api_key])
                logger.warning(f"Removed API key ending in ...{api_key[-6:]} from rotation")
                
                if not self.api_keys:
                    raise ValueError("No API keys remaining after removal!")
    
    def get_key_count(self) -> int:
        """Get the number of available API keys"""
        with self.lock:
            return len(self.api_keys)
    
    def has_multiple_keys(self) -> bool:
        """Check if multiple API keys are available"""
        return self.get_key_count() > 1


# Singleton instance
_key_manager_instance: Optional[APIKeyManager] = None
_instance_lock = threading.Lock()


def get_key_manager() -> APIKeyManager:
    """
    Get the singleton instance of APIKeyManager.
    Thread-safe lazy initialization.
    
    Returns:
        APIKeyManager instance
    """
    global _key_manager_instance
    
    if _key_manager_instance is None:
        with _instance_lock:
            if _key_manager_instance is None:
                _key_manager_instance = APIKeyManager()
    
    return _key_manager_instance


def reset_key_manager():
    """Reset the key manager instance (useful for testing)"""
    global _key_manager_instance
    with _instance_lock:
        _key_manager_instance = None
