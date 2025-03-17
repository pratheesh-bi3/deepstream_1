STORAGE_ACCOUNT_NAME = "satraining2025"
STORAGE_ACCOUNT_KEY = "GEhISN5aidY48RSRo/sS//DrglNqDiUJBQq2uPAFPnyDVS4hHiEQ6PTuFHqULcF97V7Y7f15NHZT+ASt6EJxYA=="
CONTAINER_NAME = "pratheesh-deepstream"

import sys
from azure.storage.blob import BlobServiceClient
import os

# Check if file path is provided
if len(sys.argv) < 2:
    print("Usage: python3 azure_blob.py <file_path>")
    sys.exit(1)

FILE_PATH = sys.argv[1]  # Get file path from argument

# Validate if file exists
if not os.path.isfile(FILE_PATH):
    print(f"Error: File '{FILE_PATH}' not found.")
    sys.exit(1)

# Extract filename from path to use as blob name
BLOB_NAME = os.path.basename(FILE_PATH)

# Create a BlobServiceClient
connection_string = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT_NAME};AccountKey={STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Create a container if it doesn't exist
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
try:
    container_client.create_container()
except Exception:
    pass  # Ignore error if container already exists

# Upload the file
blob_client = blob_service_client.get_blob_client(CONTAINER_NAME, BLOB_NAME)
with open(FILE_PATH, "rb") as data:
    blob_client.upload_blob(data, overwrite=True)

print(f"✅ File '{FILE_PATH}' uploaded to Azure Blob Storage as '{BLOB_NAME}'")

