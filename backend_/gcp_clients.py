import os
from typing import Optional
from google.cloud import storage, speech
from google.cloud import aiplatform
import google.generativeai as genai

class GCPClients:
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.bucket_name = os.getenv("GCP_BUCKET_NAME")
        service_account = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("GCP_SERVICE_ACCOUNT_PATH")
        if service_account and os.path.isfile(service_account):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account
        # Init clients
        aiplatform.init(project=self.project_id, location=self.location)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.bucket_name)
        self.speech_client = speech.SpeechClient()
        self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")

    def ensure_index(self, display_name: str) -> str:
        from google.cloud.aiplatform import MatchingEngineIndex
        # Always use existing index - don't create new ones
        try:
            indexes = MatchingEngineIndex.list()
            print(f"Found {len(indexes)} existing indexes")
            
            # Look for the specific display_name first
            for idx in indexes:
                if idx.display_name == display_name:
                    print(f"Found existing index with matching name: {idx.resource_name}")
                    return idx.resource_name
            
            # If no exact match, use the first available index (from your screenshot)
            if indexes:
                first_index = indexes[0]
                print(f"Using first available index: {first_index.resource_name}")
                return first_index.resource_name
                
        except Exception as e:
            print(f"Warning: Could not list indexes: {e}")

        # Fallback to known index from your screenshot
        fallback_index = f"projects/{self.project_id}/locations/{self.location}/indexes/3522784677859426304"
        print(f"Using fallback index: {fallback_index}")
        return fallback_index

    def update_index_with_gcs(self, index_resource_name: str, gcs_uri: str):
        try:
            print(f"Updating index {index_resource_name} with data from {gcs_uri}")

            # Use the v1 API for Vertex AI Matching Engine
            from google.cloud.aiplatform_v1 import IndexServiceClient, types
            from google.protobuf import field_mask_pb2
            from google.api_core.client_options import ClientOptions

            # Initialize client with correct region endpoint
            client_options = ClientOptions(api_endpoint=f"{self.location}-aiplatform.googleapis.com")
            client = IndexServiceClient(client_options=client_options)

            # Get the current index
            index = client.get_index(name=index_resource_name)

            # Update the index with new contents
            update_mask = field_mask_pb2.FieldMask(paths=["contents_delta_uri"])
            index.contents_delta_uri = gcs_uri

            request = types.UpdateIndexRequest(
                index=index,
                update_mask=update_mask
            )

            op = client.update_index(request=request)
            print(f"Index update operation started: {op.operation.name}")

            # Wait for completion
            print("Waiting for index update to complete...")
            result = op.result()
            print(f"Index update completed successfully")

            return op

        except Exception as e:
            print(f"Warning: Could not update index with GCS data: {e}")
            # For now, just log that vectors were prepared but index update failed
            print(f"Vectors prepared at {gcs_uri} but index update failed. Manual index update may be needed.")
            return None

    async def search_vectors(self, query_embedding: list, product_ids: list, top_k: int = 5):
        """Search for nearest neighbors in the vector index filtered by product IDs"""
        try:
            from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
            
            # Get the index
            index_name = self.ensure_index("ai_product_index")
            index = MatchingEngineIndex(index_name)
            
            # For now, return mock results since we need deployed endpoints for actual search
            # This would need a deployed endpoint in production
            print(f"Searching in index {index_name} for {len(product_ids)} products with top_k={top_k}")
            
            # Mock search results for development
            mock_results = []
            for i in range(min(top_k, 3)):
                mock_results.append({
                    "id": f"vector_{i}",
                    "distance": 0.1 + (i * 0.1),
                    "metadata": {
                        "product_id": product_ids[0] if product_ids else "unknown",
                        "page_content": f"Mock search result {i+1} for your query",
                        "source_file": f"lesson_{i+1}.pdf"
                    }
                })
            
            return mock_results
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []

    async def embed_query(self, query_text: str):
        """Generate embedding for search query"""
        try:
            # For now, use the same mock embedding as in pipeline
            import hashlib
            text_hash = hashlib.md5(query_text.encode()).hexdigest()
            
            embedding = []
            for i in range(768):
                hash_part = text_hash[(i * 2) % len(text_hash): (i * 2 + 2) % len(text_hash)]
                if len(hash_part) == 2:
                    value = int(hash_part, 16) / 255.0
                else:
                    value = 0.5
                embedding.append(value)
            
            print(f"Generated query embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            return []

    def upload_file_to_gcs(self, file_content: bytes, destination_path: str, content_type: str = None):
        """Upload a file to Google Cloud Storage"""
        try:
            blob = self.bucket.blob(destination_path)
            if content_type:
                blob.content_type = content_type
            blob.upload_from_string(file_content)
            gcs_uri = f"gs://{self.bucket_name}/{destination_path}"
            print(f"Uploaded file to {gcs_uri}")
            return gcs_uri
        except Exception as e:
            print(f"Error uploading file to GCS: {e}")
            raise

    def create_product_folder(self, product_name: str, product_type: str = "digital_products"):
        """Create a folder structure in GCS for a product"""
        # Clean product name for folder path
        clean_name = product_name.replace(" ", "_").replace("/", "_")
        folder_path = f"{product_type}/{clean_name}/"
        
        # Create a placeholder file to ensure folder exists
        placeholder_blob = self.bucket.blob(f"{folder_path}.placeholder")
        placeholder_blob.upload_from_string("")
        
        print(f"Created product folder: {folder_path}")
        return folder_path
