from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.repositories.product_repository import ProductRepository


UPLOAD_DIR = Path("uploads/products")

ALLOWED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ProductService:

    @staticmethod
    def get_all_products(db: Session):
        return ProductRepository.get_all(db)

    @staticmethod
    def create_product(
        db: Session,
        name: str,
        description: str | None,
        image: UploadFile
    ):
        if image.content_type not in ALLOWED_IMAGES:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG and WEBP images are allowed"
            )

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        extension = ALLOWED_IMAGES[image.content_type]
        filename = f"{uuid4().hex}{extension}"
        image_path = UPLOAD_DIR / filename

        try:
            with image_path.open("wb") as file:
                while chunk := image.file.read(1024 * 1024):
                    file.write(chunk)

            product_data = {
                "name": name,
                "description": description,
                "image": image_path.as_posix()
            }

            return ProductRepository.create(db, product_data)

        except Exception:
            image_path.unlink(missing_ok=True)
            raise



    @staticmethod
    def update_product(
        db: Session,
        product_id: int,
        name: str | None,
        description: str | None,
        image: UploadFile | None
    ):
        product = ProductRepository.get_by_id(db, product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product_data = {}

        if name is not None:
            product_data["name"] = name

        if description is not None:
            product_data["description"] = description

        if image is not None:
            if image.content_type not in ALLOWED_IMAGES:
                raise HTTPException(
                    status_code=400,
                    detail="Only JPG, PNG and WEBP images are allowed"
                )

            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

            extension = ALLOWED_IMAGES[image.content_type]
            filename = f"{uuid4().hex}{extension}"
            image_path = UPLOAD_DIR / filename

            with image_path.open("wb") as file:
                while chunk := image.file.read(1024 * 1024):
                    file.write(chunk)

            product_data["image"] = image_path.as_posix()

        return ProductRepository.update(db, product, product_data)




    @staticmethod
    def get_product_by_id(db: Session, product_id: int):
        product = ProductRepository.get_by_id(db, product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        return product


    @staticmethod
    def delete_product(db: Session, product_id: int):
        product = ProductRepository.get_by_id(db, product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        ProductRepository.delete(db, product)

        return {"message": "Product deleted successfully"}



    