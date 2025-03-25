# src/config_loader.py
import yaml
import os
from typing import Dict, Any # Import Dict and Any for return type hint

def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """Loads the configuration file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
            # Basic validation (can be expanded)
            if not config:
                raise ValueError("Configuration file is empty or invalid.")
            if 'coinbase' not in config or 'trading' not in config or 'strategies' not in config:
                 raise ValueError("Missing required sections in config: 'coinbase', 'trading', 'strategies'")
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while loading config: {e}")

if __name__ == '__main__':
    # Example usage when run directly
    try:
        # Assuming config.yaml is in the parent directory relative to src/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file_path = os.path.join(project_root, 'config.yaml')
        cfg = load_config(config_file_path)
        print("Configuration loaded successfully:")
        print(cfg)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error loading configuration: {e}")