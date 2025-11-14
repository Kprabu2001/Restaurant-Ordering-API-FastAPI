# main.py
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field,ConfigDict
from sqlalchemy import (create_engine, Column, Integer, String, Text, Numeric,
                        Boolean, ForeignKey, DateTime, func,or_)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from dotenv import load_dotenv



load_dotenv()  #.env support


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Please configure it in your .env file.")


engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False)

Base = declarative_base()

# --------------------
# ORM models
# --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(200), unique=True, nullable=False)

    carts = relationship("Cart", back_populates="user")


class Restaurant(Base):
    __tablename__ = "restaurants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    cuisine = Column(String(100))
    rating = Column(Numeric(2,1), default=0.0)

    menu_items = relationship("MenuItem", back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10,2), nullable=False)
    is_available = Column(Boolean, default=True)

    restaurant = relationship("Restaurant", back_populates="menu_items")


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="open")  # open or checked_out
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    qty = Column(Integer, nullable=False)
    price_at_add = Column(Numeric(10,2), nullable=False)
   

    cart = relationship("Cart", back_populates="items")
    menu_item = relationship("MenuItem")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), unique=True, nullable=False)
    placed_at = Column(DateTime(timezone=True), server_default=func.now())
    total_amount = Column(Numeric(12,2), nullable=False)
    
Base.metadata.create_all(engine)


# --------------------
# Pydantic schemas
# --------------------
class UserCreate(BaseModel):
    name: str
    email: str




class RestaurantOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    cuisine: Optional[str]
    rating: Optional[Decimal]
    
    model_config = ConfigDict(from_attributes=True) 

class CartCreate(BaseModel):
            user_id: Optional[int] = None       


class MenuItemOut(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str]
    price: Decimal
    is_available: bool

    model_config = ConfigDict(from_attributes=True)
        
       



class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    is_available: Optional[bool] = True



class CartItemIn(BaseModel):
    menu_item_id: int
    qty: int = Field(..., gt=0)


class CartItemOut(BaseModel):
    id: int
    menu_item_id: int
    qty: int
    price_at_add: float

    model_config = ConfigDict(from_attributes=True)

    

class CartOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    status: str
    created_at: datetime
    items: Optional[List[CartItemOut]] = None

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    cart_id: int
    placed_at: datetime
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)
        

# --------------------
# Dependency
# --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------
# App and endpoints
# --------------------
app = FastAPI(title="Restaurant Booking / Ordering API", version="1.0")



# -- Users 
@app.post("/users", response_model=UserCreate, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(name=payload.name, email=payload.email)
    db.add(user)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Email already exists:{str(e)}")
    db.refresh(user)
    return payload


# -- Restaurants
@app.get("/restaurants", response_model=List[RestaurantOut])
def list_restaurants(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(Restaurant).offset(skip).limit(limit).all()
    return rows


@app.get("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return r


@app.get("/restaurants/{restaurant_id}/menu", response_model=List[MenuItemOut])
def get_menu(restaurant_id: int, db: Session = Depends(get_db)):
    items = db.query(MenuItem).filter(MenuItem.restaurant_id == restaurant_id).all()
    return items


# -- Menu items (for adding items )
@app.post("/restaurants/{restaurant_id}/menu", response_model=MenuItemOut, status_code=201)
def create_menu_item(restaurant_id: int, payload: MenuItemCreate, db: Session = Depends(get_db)):
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        is_available=payload.is_available
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# -- Search for restaurants or menu items

@app.get("/search")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    qlike = f"%{q.lower()}%"

    restaurants = db.query(Restaurant).filter(
        or_(
            func.lower(Restaurant.name).like(qlike),
            func.lower(Restaurant.cuisine).like(qlike)
        )
    ).limit(20).all()

    menu = db.query(MenuItem).filter(
        or_(
            func.lower(MenuItem.name).like(qlike),
            func.lower(func.coalesce(MenuItem.description, '')).like(qlike)
        )
    ).limit(50).all()

    return {
        "restaurants": [RestaurantOut.model_validate(r, from_attributes=True) for r in restaurants],
        "menu_items": [MenuItemOut.model_validate(m, from_attributes=True) for m in menu]
    }

# -- Cart operations
@app.post("/carts", response_model=CartOut, status_code=201)
def create_cart(payload: CartCreate, db: Session = Depends(get_db)):
    # Check if user exists (if provided)
    if payload.user_id is not None:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    # Create cart
    cart = Cart(user_id=payload.user_id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart




@app.get("/carts/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


@app.post("/carts/{cart_id}/items", response_model=CartOut)
def add_item_to_cart(cart_id: int, payload: CartItemIn, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.status == "open").first()
    if not cart:
        raise HTTPException(status_code=404, detail="Open cart not found")
    menu_item = db.query(MenuItem).filter(MenuItem.id == payload.menu_item_id, MenuItem.is_available == True).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not available")
    # If item already exists in cart, increase qty
    existing = db.query(CartItem).filter(CartItem.cart_id == cart_id, CartItem.menu_item_id == payload.menu_item_id).first()
    if existing:
        existing.qty += payload.qty
        db.add(existing)
    else:
        ci = CartItem(cart_id=cart_id, menu_item_id=payload.menu_item_id, qty=payload.qty, price_at_add=menu_item.price)
        db.add(ci)
    db.commit()
    db.refresh(cart)
    return cart


@app.put("/carts/{cart_id}/items/{menu_item_id}", response_model=CartOut)
def update_item_qty(cart_id: int, menu_item_id: int, qty: int = Body(..., embed=True), db: Session = Depends(get_db)):
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")
    ci = db.query(CartItem).filter(CartItem.cart_id == cart_id, CartItem.menu_item_id == menu_item_id).first()
    if not ci:
        raise HTTPException(status_code=404, detail="Cart item not found")
    ci.qty = qty
    db.add(ci)
    db.commit()
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    return cart


@app.delete("/carts/{cart_id}/items/{menu_item_id}", response_model=CartOut)
def remove_item_from_cart(cart_id: int, menu_item_id: int, db: Session = Depends(get_db)):
    ci = db.query(CartItem).filter(CartItem.cart_id == cart_id, CartItem.menu_item_id == menu_item_id).first()
    if not ci:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(ci)
    db.commit()
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    return cart


# -- Checkout (simple)


@app.post("/carts/{cart_id}/checkout", response_model=OrderOut)
def checkout(cart_id: int, db: Session = Depends(get_db)):
    # 1. Get open cart
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.status == "open").first()
    if not cart:
        raise HTTPException(status_code=404, detail="Open cart not found")
    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 2. Calculate total safely
    total = sum(
        Decimal(item.qty) * Decimal(item.price_at_add or 0) for item in cart.items
    )

    # 3. Create order
    order = Order(id=cart.id, cart_id=cart.id, total_amount=total)

    cart.status = "checked_out"

    try:
        db.add(order)
        db.add(cart)
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")

    return order
