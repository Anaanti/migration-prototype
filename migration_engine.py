import os
import json
import shutil
import csv
from datetime import datetime

# -----------------------------
# PATH SETUP
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

METADATA_FILE = os.path.join(BASE_DIR, "metadata", "file_index.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config", "structure_config.json")
STAGING_DIR = os.path.join(BASE_DIR, "staging", "raw_files")
FINAL_DIR = os.path.join(BASE_DIR, "final_storage")

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

MIGRATION_LOG = os.path.join(LOG_DIR, "migration_log.csv")
ERROR_LOG = os.path.join(LOG_DIR, "error_log.txt")

os.makedirs(FINAL_DIR, exist_ok=True)

# -----------------------------
# LOAD CONFIGS
# -----------------------------
with open(METADATA_FILE, "r") as f:
    metadata = json.load(f)

with open(CONFIG_FILE, "r") as f:
    structure_config = json.load(f)

levels = structure_config["levels"]
filename_pattern = structure_config["filename_pattern"]

# -----------------------------
# INIT CSV LOG
# -----------------------------
with open(MIGRATION_LOG, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["timestamp", "source_path", "target_path", "index_id"])

# -----------------------------
# MIGRATION PROCESS
# -----------------------------
for file_name in os.listdir(STAGING_DIR):

    source_path = os.path.join(STAGING_DIR, file_name)

    if not os.path.isfile(source_path):
        continue

    try:
        if file_name not in metadata:
            raise ValueError("Missing metadata")

        file_info = metadata[file_name]

        # Build target directory dynamically
        target_dir = FINAL_DIR
        for level in levels:
            if level not in file_info:
                raise KeyError(f"Missing metadata key: {level}")
            target_dir = os.path.join(target_dir, file_info[level])

        os.makedirs(target_dir, exist_ok=True)

        new_name = file_name

        target_path = os.path.join(target_dir, new_name)

        shutil.copy2(source_path, target_path)

        # Log success
        with open(MIGRATION_LOG, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                datetime.utcnow().isoformat(),
                source_path,
                target_path,
                file_info.get("index_id", "N/A") # Uses "N/A" if index_id is deleted
            ])

        print(f"Migrated: {file_name}")

    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as err:
            err.write(
                f"[{datetime.utcnow().isoformat()}] {file_name} → {str(e)}\n"
            )

        print(f"Error processing {file_name}: {e}")
