import os
import json
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pg8000
import hashlib
import hmac
import base64

from gcp_clients import GCPClients
from pipeline import ProcessingPipeline
from db_layer import DBLayer

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GCP_SERVICE_ACCOUNT_PATH")
os.environ["GCP_PROJECT_ID"] = 'isabi-469615'

# JWT Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback_secret_key')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="Add AI Train Product API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize shared services
clients = GCPClients()
db = DBLayer()
pipeline = ProcessingPipeline(clients)
security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str

class AdminCreateRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    phone_number: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    name: str
    role: str

class AddProductResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class SearchResponse(BaseModel):
    success: bool
    message: str
    query: str
    product_ids: List[str]
    results: List[dict]
    total_results: int

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Simple JWT-like token creation using HMAC
    payload = json.dumps(to_encode, default=str)
    signature = hmac.new(
        SECRET_KEY.encode(), 
        payload.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    token = base64.b64encode(f"{payload}.{signature}".encode()).decode()
    return token

def verify_token(token: str):
    try:
        decoded = base64.b64decode(token.encode()).decode()
        payload_str, signature = decoded.rsplit('.', 1)
        
        expected_signature = hmac.new(
            SECRET_KEY.encode(), 
            payload_str.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
            
        payload = json.loads(payload_str)
        
        # Check expiration
        exp = datetime.fromisoformat(payload.get('exp', ''))
        if datetime.utcnow() > exp:
            return None
            
        return payload
    except:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("sub")

@app.get("/health")
def health():
    return {"status": "ok", "project": clients.project_id, "bucket": clients.bucket_name}

# Authentication endpoints
@app.post("/super_admin/login", response_model=LoginResponse)
async def super_admin_login(request: LoginRequest):
    with db.transaction() as conn:
        result = db.get_super_admin_by_credentials(conn, request.email, request.password)
        
        if result:
            admin_id, name = result
            access_token = create_access_token({"sub": str(admin_id)})
            return LoginResponse(
                access_token=access_token,
                name=name,
                role="super_admin"
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/admin/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    with db.transaction() as conn:
        result = db.get_sub_admin_by_credentials(conn, request.email, request.password)
        
        if result:
            admin_id, name = result
            access_token = create_access_token({"sub": str(admin_id)})
            return LoginResponse(
                access_token=access_token,
                name=name,
                role="sub_admin"
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/super_admin/insert")
async def insert_super_admin(request: AdminCreateRequest):
    with db.transaction() as conn:
        try:
            admin_id = db.insert_super_admin(conn, request.name, request.email, request.password, request.phone)
            return {"message": "Super admin created", "admin_id": str(admin_id)}
        except pg8000.Error as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.post("/admin/insert")
async def insert_admin(request: AdminCreateRequest, current_user: str = Depends(get_current_user)):
    with db.transaction() as conn:
        if not db.is_super_admin(conn, current_user):
            raise HTTPException(status_code=403, detail="Only super admin can insert sub admin")
        
        try:
            sub_admin_id = db.insert_sub_admin(conn, request.name, current_user, request.email, request.phone_number, request.password)
            return {"message": "Sub admin created", "sub_admin_id": str(sub_admin_id)}
        except pg8000.Error as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/view_table")
async def view_table(table: str = Query(..., description="Table name to view"), 
                    current_user: str = Depends(get_current_user)):
    with db.transaction() as conn:
        if not (db.is_super_admin(conn, current_user) or db.is_sub_admin(conn, current_user)):
            raise HTTPException(status_code=403, detail="Admin access required")
    
        # List of allowed tables
        allowed_tables = [
            'super_admins', 'sub_admins', 'users', 'product_types', 'products',
            'digital_products', 'ai_train_products', 'ai_train_product_details',
            'payments', 'user_purchases', 'user_activity_log', 'sub_admin_activity_log',
            'super_admin_activity_log', 'chat_sessions', 'vector_metadata'
        ]
        
        if table.lower() not in allowed_tables:
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        try:
            data = db.get_table_data(conn, table)
            return {"data": data}
        except pg8000.Error as e:
            raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/add-ai-train-product", response_model=AddProductResponse)
async def add_ai_train_product(
    admin_id: str = Form(...),
    admin_type: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(...),
    suggestion_questions: Optional[str] = Form(None),
    price: float = Form(...),
    videos: List[UploadFile] = File(...)
):
    print(f"Received request with admin_id: {admin_id}, admin_type: {admin_type}, product_name: {product_name}")
    print(f"Price: {price}, videos count: {len(videos) if videos else 0}")
    
    # Validate admin_type
    if admin_type not in ("super_admin", "sub_admin"):
        print(f"Invalid admin_type: {admin_type}")
        raise HTTPException(status_code=400, detail="admin_type must be 'super_admin' or 'sub_admin'")

    # Parse suggestion_questions
    suggestions_json = None
    if suggestion_questions:
        print(f"Parsing suggestion_questions: {suggestion_questions}")
        try:
            suggestions_json = json.loads(suggestion_questions)
            if not isinstance(suggestions_json, list):
                raise ValueError("suggestion_questions must be a JSON array")
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text and split by newlines
            suggestions_json = [q.strip() for q in suggestion_questions.split('\n') if q.strip()]
        except ValueError as e:
            print(f"Error parsing suggestion_questions: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    # Ensure vector index exists
    v_index_name = await pipeline.ensure_vector_index("ai_product_index")  # Fixed typo
    print(f"Vector index: {v_index_name}")

    # Ensure bucket product folder structure exists
    root_prefix = await pipeline.ensure_product_folders(product_name)

    # Start DB transaction for product records
    with db.transaction() as conn:
        # 1) Insert into products
        product_id = db.insert_product(
            conn=conn,
            product_name=product_name,
            product_category=product_category,
            price=price,
            admin_id=admin_id,
            admin_type=admin_type
        )

        # 2) Insert into ai_train_products (vector count later updated)
        db.insert_ai_train_product(
            conn=conn,
            product_id=product_id,
            product_name=product_name,
            product_category=product_category,
            suggestion_questions=suggestions_json,
            product_vector_id=None,
            number_of_videos=0
        )

    # Process each video: upload -> audio -> transcribe -> PDF -> embeddings
    results = await pipeline.process_videos(
        product_name=product_name,
        product_id=str(product_id),
        videos=videos
    )

    # Count vectors and insert/update DB records
    total_vectors = 0
    with db.transaction() as conn:
        # Update ai_train_products counts and product_vector_id (store total vectors as requested)
        product_vector_id = str(sum(len(it.get("vectors", [])) for it in results.get("items", [])))
        number_of_videos = len(results.get("items", []))
        db.update_ai_train_product(
            conn=conn,
            product_id=product_id,
            product_vector_id=product_vector_id,
            number_of_videos=number_of_videos
        )

        # Details and vector_metadata
        for i, item in enumerate(results.get("items", []), start=1):
            # Insert details
            db.insert_ai_train_product_detail(
                conn=conn,
                product_id=product_id,
                video_path=item["video_gcs"],
                audio_path=item["audio_gcs"],
                text_path=item["text_gcs"],
                pdf_path=item["pdf_gcs"],
                lesson_title=item["lesson_title"],
                lesson_order=i,
                metadata=item.get("metadata")
            )

            # Vector metadata rows
            for vec in item.get("vectors", []):
                total_vectors += 1
                db.insert_vector_metadata(
                    conn=conn,
                    product_id=product_id,
                    vector_index_name=v_index_name,
                    content_type="ai_training_content",
                    source_file_path=item["pdf_gcs"],
                    metadata=vec.get("metadata"),
                )

    return JSONResponse(
        content={
            "success": True,
            "message": "AI training product added",
            "data": {
                "product_id": str(product_id),
                "product_name": product_name,
                "bucket_root": root_prefix,
                "vector_index": v_index_name,
                "number_of_videos": len(results.get("items", [])),
                "total_vectors": total_vectors,
                "items": results.get("items", [])
            },
        },
        status_code=200,
    )

@app.get("/api/search-vectors", response_model=SearchResponse)
async def search_vectors(
    question: str = Query(..., description="Search question"),
    product_ids: str = Query(..., description="Comma-separated list of product IDs"),
    n: int = Query(5, description="Number of nearest neighbors to return")
):
    """Search for nearest neighbors in vector database for specific products"""
    try:
        # Parse product IDs
        product_id_list = [pid.strip() for pid in product_ids.split(',') if pid.strip()]
        
        if not product_id_list:
            raise HTTPException(status_code=400, detail="At least one product_id is required")
        
        if n <= 0 or n > 50:
            raise HTTPException(status_code=400, detail="n must be between 1 and 50")
        
        print(f"Searching for question: '{question}' in products: {product_id_list}, top {n} results")
        
        # Verify products exist in database
        with db.transaction() as conn:
            vector_metadata = db.get_product_vectors(conn, product_id_list)
            
        if not vector_metadata:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "No vectors found for the specified product IDs",
                    "query": question,
                    "product_ids": product_id_list,
                    "results": [],
                    "total_results": 0
                },
                status_code=404
            )
        
        # Generate embedding for the search query
        query_embedding = await clients.embed_query(question)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding for query")
        
        # Search vectors in the index
        search_results = await clients.search_vectors(
            query_embedding=query_embedding,
            product_ids=product_id_list,
            top_k=n
        )
        
        # Format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "vector_id": result.get("id"),
                "similarity_score": 1.0 - result.get("distance", 0),  # Convert distance to similarity
                "content": result.get("metadata", {}).get("page_content", ""),
                "source_file": result.get("metadata", {}).get("source_file", ""),
                "product_id": result.get("metadata", {}).get("product_id", ""),
                "lesson_no": result.get("metadata", {}).get("lesson_no", ""),
                "page": result.get("metadata", {}).get("page", "")
            })
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Found {len(formatted_results)} results",
                "query": question,
                "product_ids": product_id_list,
                "results": formatted_results,
                "total_results": len(formatted_results)
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in vector search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/products")
async def get_products():
    """Get all AI training products for reference"""
    try:
        with db.transaction() as conn:
            products = db.get_all_products(conn)
        
        formatted_products = []
        for product in products:
            formatted_products.append({
                "product_id": str(product[0]),
                "product_name": product[1],
                "product_category": product[2],
                "number_of_videos": product[3],
                "product_vector_id": product[4],
                "suggestion_questions": json.loads(product[5]) if product[5] else [],
                "created_at": product[6].isoformat() if product[6] else None
            })
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Found {len(formatted_products)} products",
                "products": formatted_products
            },
            status_code=200
        )
        
    except Exception as e:
        print(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Digital Product endpoints
@app.post("/api/add-digital-product")
async def add_digital_product(
    admin_id: str = Form(...),
    admin_type: str = Form(...),
    product_name: str = Form(...),
    product_category: str = Form(...),
    product_description: str = Form(...),
    price: float = Form(...),
    product_file: UploadFile = File(...)
):
    """Add a digital product with file upload and vector embedding"""
    print(f"Received digital product: {product_name}, category: {product_category}")
    
    # Validate admin_type
    if admin_type not in ("super_admin", "sub_admin"):
        raise HTTPException(status_code=400, detail="admin_type must be 'super_admin' or 'sub_admin'")
    
    try:
        # Read file content
        file_content = await product_file.read()
        file_size_mb = len(file_content) / (1024 * 1024)  # Convert to MB
        
        # Get file format
        file_format = product_file.filename.split('.')[-1] if '.' in product_file.filename else 'unknown'
        
        # Create folder in GCS for digital products
        folder_path = clients.create_product_folder(product_name, "digital_products")
        
        # Upload file to GCS
        file_destination = f"{folder_path}{product_file.filename}"
        product_location = clients.upload_file_to_gcs(
            file_content, 
            file_destination,
            product_file.content_type
        )
        
        # Ensure digital_product vector index exists
        digital_index_name = clients.ensure_index("digital_product_index")
        print(f"Using vector index: {digital_index_name}")
        
        # Generate embedding for product description
        description_embedding = await clients.embed_query(product_description)
        
        # Start database transaction
        with db.transaction() as conn:
            # Insert into products table
            product_id = db.insert_product(
                conn=conn,
                product_name=product_name,
                product_category=product_category,
                price=price,
                admin_id=admin_id,
                admin_type=admin_type
            )
            
            # Insert into digital_products table
            db.insert_digital_product(
                conn=conn,
                product_id=product_id,
                product_name=product_name,
                product_category=product_category,
                product_location=product_location,
                product_size_mb=file_size_mb,
                file_format=file_format,
                description=product_description
            )
            
            # Insert vector metadata
            vector_metadata = {
                "product_id": str(product_id),
                "product_name": product_name,
                "product_category": product_category,
                "description": product_description,
                "product_location": product_location,
                "file_format": file_format,
                "file_size_mb": file_size_mb,
                "embedding": description_embedding[:10]  # Store first 10 dims as sample
            }
            
            db.insert_vector_metadata(
                conn=conn,
                product_id=product_id,
                vector_index_name=digital_index_name,
                content_type="digital_product",
                source_file_path=product_location,
                metadata=vector_metadata
            )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Digital product added successfully",
                "data": {
                    "product_id": str(product_id),
                    "product_name": product_name,
                    "product_category": product_category,
                    "product_location": product_location,
                    "file_size_mb": round(file_size_mb, 2),
                    "file_format": file_format,
                    "vector_index": digital_index_name,
                    "description": product_description
                }
            },
            status_code=200
        )
        
    except Exception as e:
        print(f"Error adding digital product: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/digital-products")
async def get_digital_products():
    """Get all digital products"""
    try:
        with db.transaction() as conn:
            products = db.get_all_digital_products(conn)
        
        formatted_products = []
        for product in products:
            formatted_products.append({
                "product_id": str(product[0]),
                "product_name": product[1],
                "product_category": product[2],
                "product_location": product[3],
                "product_size_mb": float(product[4]) if product[4] else 0,
                "file_format": product[5],
                "created_at": product[6].isoformat() if product[6] else None,
                "price": float(product[7]) if product[7] else 0
            })
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Found {len(formatted_products)} digital products",
                "products": formatted_products
            },
            status_code=200
        )
        
    except Exception as e:
        print(f"Error getting digital products: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/search-digital-products")
async def search_digital_products(
    query: str = Query(..., description="Search query"),
    n: int = Query(5, description="Number of results to return")
):
    """Search digital products using vector similarity"""
    try:
        if n <= 0 or n > 50:
            raise HTTPException(status_code=400, detail="n must be between 1 and 50")
        
        print(f"Searching digital products for: '{query}', top {n} results")
        
        # Generate embedding for search query
        query_embedding = await clients.embed_query(query)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding for query")
        
        # Get all digital products from database
        with db.transaction() as conn:
            products = db.get_all_digital_products(conn)
        
        if not products:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "No digital products found",
                    "query": query,
                    "results": [],
                    "total_results": 0
                },
                status_code=404
            )
        
        # For now, return mock similarity search results
        # In production, this would use actual vector search
        results = []
        for i, product in enumerate(products[:n]):
            # Calculate mock similarity score (in production, use actual cosine similarity)
            similarity_score = 0.95 - (i * 0.05)
            
            results.append({
                "product_id": str(product[0]),
                "product_name": product[1],
                "product_category": product[2],
                "product_location": product[3],
                "product_size_mb": float(product[4]) if product[4] else 0,
                "file_format": product[5],
                "price": float(product[7]) if product[7] else 0,
                "similarity_score": similarity_score
            })
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Found {len(results)} results",
                "query": query,
                "results": results,
                "total_results": len(results)
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error searching digital products: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
