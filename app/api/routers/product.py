from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import ProductResponse
from app.services.product_service import ProductService

router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    name: str = Form(...),
    description: str | None = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return ProductService.create_product(
        db=db,
        name=name,
        description=description,
        image=image
    )



@router.get(
        "/", 
    response_model=list[ProductResponse])
def get_all_products(db: Session = Depends(get_db)):
    return ProductService.get_all_products(db)




@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    return ProductService.update_product(
        db=db,
        product_id=product_id,
        name=name,
        description=description,
        image=image
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db)
):
    return ProductService.get_product_by_id(db, product_id)


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    return ProductService.delete_product(db, product_id)

