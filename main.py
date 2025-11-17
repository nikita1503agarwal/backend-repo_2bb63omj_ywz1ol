import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson.objectid import ObjectId

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------------------
# E-COMMERCE ENDPOINTS
# ---------------------
class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image: Optional[str] = None
    badge: Optional[str] = None


def _product_to_dict(doc: dict) -> dict:
    d = dict(doc)
    if d.get("_id"):
        d["id"] = str(d.pop("_id"))
    return d


@app.get("/api/products", response_model=List[dict])
def list_products():
    try:
        from database import db
        # Auto-seed if empty for demo
        count = db["product"].count_documents({})
        if count == 0:
            seed_products = [
                {
                    "title": "Aurora Cube Lamp",
                    "description": "Futuristic RGB glass cube lamp with reactive glow.",
                    "price": 149.0,
                    "category": "Lighting",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1557264337-e8a93017fe92?q=80&w=1200&auto=format&fit=crop",
                    "badge": "New"
                },
                {
                    "title": "Nebula Headphones",
                    "description": "Spatial audio with adaptive ANC in a sleek titanium finish.",
                    "price": 299.0,
                    "category": "Audio",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1518444082625-79a48bb0faaa?q=80&w=1200&auto=format&fit=crop",
                    "badge": "Bestseller"
                },
                {
                    "title": "Quantum Desk Mat",
                    "description": "Soft-touch XL mat with nano-texture and underglow.",
                    "price": 59.0,
                    "category": "Accessories",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1516387938699-a93567ec168e?q=80&w=1200&auto=format&fit=crop",
                    "badge": "Limited"
                },
                {
                    "title": "Flux Mechanical Keyboard",
                    "description": "Hot-swappable switches, per-key RGB, aluminum chassis.",
                    "price": 189.0,
                    "category": "Keyboards",
                    "in_stock": True,
                    "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=1200&auto=format&fit=crop",
                    "badge": None
                },
            ]
            if db is None:
                raise HTTPException(status_code=500, detail="Database not configured")
            for p in seed_products:
                db["product"].insert_one(p)

        products = list(db["product"].find().limit(24))
        return [_product_to_dict(p) for p in products]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate):
    try:
        from database import db
        if db is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        data = product.model_dump()
        res = db["product"].insert_one(data)
        created = db["product"].find_one({"_id": res.inserted_id})
        return _product_to_dict(created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        from database import db
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="Invalid id")
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")
        return _product_to_dict(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
