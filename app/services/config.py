from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent / "config.yml"

# with open("app/services/config.yml", "r") as f:
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)
