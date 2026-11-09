from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:

    @staticmethod
    def create(db: Session, product_data: dict):

        product = Product(**product_data)

        db.add(product)
        db.commit()
        db.refresh(product)

        return product



    @staticmethod
    def update(db: Session, product: Product, product_data: dict):
        for key, value in product_data.items():
            setattr(product, key, value)

        db.commit()
        db.refresh(product)

        return product


    @staticmethod
    def get_by_id(db: Session, product_id: int):

        return db.query(Product).filter(
            Product.id == product_id
        ).first()

    @staticmethod
    def get_all(db: Session):

        return db.query(Product).all()

    @staticmethod
    def delete(db: Session, product: Product):

        db.delete(product)
        db.commit()

        return True
