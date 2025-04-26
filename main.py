from fastapi import FastAPI,UploadFile,HTTPException,Depends,status,Query
from fastapi.responses import JSONResponse,FileResponse
import aiofiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel,EmailStr
from my_best_proj import analyze_image
import io
import bcrypt
from PIL import Image
import numpy as np
from database_structure import User,session
import auth
from pathlib import Path
from typing import Optional
from mua import complementary_color
from my_best_proj import (
    load_clothing_model,
    remove_background,
    get_dominant_colors,
    classify_clothing,
)
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
import requests
from deep_translator import GoogleTranslator
from mongo_db_structure import DB,WorkWithDB
import uuid
import os
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, Depends
from fastapi.encoders import jsonable_encoder 
from fastapi import Form, UploadFile, File  
from typing import List
app = FastAPI()
secur = HTTPBearer(auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model = load_clothing_model()
http_bearer = HTTPBearer()
api_key = "f17e3812ad4343d198e143005250804"

class Reg_schema(BaseModel):
    name:str
    password:str
    email:EmailStr
class login_schema(BaseModel):
    name:str
    password:str
class weather_for_clothes_schema(BaseModel):
    city:str
class favorite_brands(BaseModel):
    brands:str
class set_favorite(BaseModel):
    id_post:str
    
RECOMMENDATIONS = {
    "Футболка/топ": "Шорты/Брюки/Юбка/Джинсы/Пальто/Кардиган/Жилет/Косуха/Бомбер/Ветровка/Комбинезон",
    "Брюки": "Рубашка/Худи/Футболка/Свитер/Лонгслив/Пальто/Сандали/Кроссовки/Ботинки/Туфли/Мокасины/Блузка/Пиджак",
    "Свитер": "Брюки/Джинсы/Юбка/Леггинсы/Пальто/Платье-комбинация/Шарф/Шапка/Перчатки/Сапоги/Лоферы",
    "Платье": "Сандали/Джинсовая рубашка/Ботильоны/Кроссовки/Косуха/Пиджак/Кардиган/Тренч/Шляпа/Сумка клатч/Колье",
    "Пальто": "Джинсы/Футболка/Юбка/Рубашка/Брюки/Свитер/Платье/Боди/Гольф/Шарф/Шапка/Перчатки/Сапоги/Челси",
    "Сандали": "Платье/Шорты/Брюки/Юбка/Комбинезон/Сарафан/Шорты-бермуды/Майка/Кроп-топ/Пляжная туника",
    "Рубашка": "Пальто/Брюки/Шорты/Юбка/Жилетка/Галстук/Бабочка/Кардиган/Джинсы-скинни/Бермуды/Босоножки",
    "Кроссовки": "Шорты/Джинсы/Брюки/Футболка/Свитер/Худи/Леггинсы/Спортивный костюм/Ветровка/Оверсайз-рубашка",
    "Сумка": "Сумка спортивная: Спортивная одежда/Кроссовки/Худи; Сумка классика: Кэжуал стиль/Пиджак/Рубашка; Сумка c принтами: Носить с простой одеждой/Монохромные вещи/Деним",
    "Ботинки": "Джинсы/Брюки/Юбка/Пальто/Штаны/Толстовка/Косуха/Платье миди/Кожаная куртка/Гольф/Шарф",
}


def check_token(token:str | bytes):
    return auth.decode_jwt(token)

@app.post("/home/send_photo")
async def analyze_clothing(file: UploadFile):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Требуется изображение")

    try:
        image_data = await file.read()
        img = Image.open(io.BytesIO(image_data))
        
        no_bg = remove_background(img)
        dominant_colors = get_dominant_colors(np.array(no_bg))
        clothing_type = classify_clothing(no_bg, model)
        
        
        def rgb_to_hex(color):
            
            r, g, b = map(int, color[:3])  
            return f"#{r:02x}{g:02x}{b:02x}"
        
        response = {
            "colors": [rgb_to_hex(color) for color in dominant_colors],
            "clothing_type": clothing_type,
            "recommendations": RECOMMENDATIONS.get(clothing_type, []),
            "complementary_colors": [rgb_to_hex(complementary_color(c)) for c in dominant_colors]
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки изображения: {str(e)}")



        

#это скорее всего будет в конце
@app.get("/home")
def Home():
    pass


#сделать бд хотя бы и начать делать регу
@app.post("/home/reg")
def reg(data: Reg_schema):
    try:
        with session as s:
            
            existing_user = s.query(User).filter((User.name == data.name) | (User.email == data.email)).first()
            if existing_user:
                return JSONResponse(
                    status_code=400,
                    content={"message": "This nickname is already taken, think of another one"}
                )
            

            
           
            hashed_password = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
            new_user = User(name=data.name, password=hashed_password, email=data.email)
            
            s.add(new_user)
            s.commit()
            
            
            s.refresh(new_user)
            
            
            jwt_payload = {
                "sub": str(new_user.id),  
                "username": new_user.name,
            }
            token = auth.encode_jwt(payload=jwt_payload)
            
            return {
                "success": "You registered successfully",
                "token": token,
                "user": {
                    "name": new_user.name,
                    "email": new_user.email
                }
            }
            
    except Exception as e:
        s.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating account: {str(e)}"
        )

#думаю на сл выходных начну по тихоньку делать или на недели учебной
@app.post("/home/login")
def login(data: login_schema) :
    try:
        with session as s:
            result = s.query(User).filter(User.name == data.name).one_or_none()
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            if not bcrypt.checkpw(data.password.encode(), result.password.encode()):
                raise HTTPException(status_code=401, detail="Incorrect password")
            jwt_payload = {
                "sub":str(result.id),
                "username": result.name,
                
            }
            token = auth.encode_jwt(payload=jwt_payload)
            return {
    "token": token,
    "token_type": "Bearer"
}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Logging in {e}")
@app.post("/home/weather&clothes")
def clothes_for_weather(data: weather_for_clothes_schema):
    
    city_on_en = GoogleTranslator(source='ru', target='en').translate(data.city)
    
    
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city_on_en}"
    response = requests.get(url)
    weather_data = response.json()
    
    temp_c = weather_data['current']['temp_c']
    condition = weather_data['current']['condition']['text']
    translated_condition = GoogleTranslator(source='en', target="ru").translate(condition)
    
    
    if temp_c > 25:
        clothes_recommendation = "Рекомендуется легкая одежда: шорты, футболка, сандалии. Не забудьте солнцезащитные очки и головной убор!"
    elif 15 <= temp_c <= 25:
        clothes_recommendation = "Идеальная погода для джинсов и рубашки/блузки. Можно надеть легкую куртку или свитер на вечер."
    elif 5 <= temp_c < 15:
        clothes_recommendation = "Прохладно, рекомендуется надеть теплую куртку, джинсы, закрытую обувь. Возможно, понадобится шарф."
    else:
        clothes_recommendation = "Холодно! Наденьте зимнюю куртку, шапку, шарф, перчатки и теплую обувь."
    
    
    if "rain" in condition.lower():
        clothes_recommendation += " И не забудьте зонт или дождевик!"
    elif "snow" in condition.lower():
        clothes_recommendation += " Обувь должна быть непромокаемой и с хорошим протектором."
    elif "sun" in condition.lower() or "clear" in condition.lower():
        clothes_recommendation += " Используйте солнцезащитный крем!"
    
    weather_info = {
        "city": data.city,
        "temperature_c": temp_c,
        "weather_condition": translated_condition,
        "clothes_recommendation": clothes_recommendation
    } 
    
    return weather_info
async def verify_user(credentials: HTTPAuthorizationCredentials = Depends(secur)):
    token = credentials.credentials
    try:
        if isinstance(token, bytes):
            token = token.decode('utf-8')
            
        payload = auth.decode_jwt(token)
        user_id = payload.get("sub")  
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
            
        with session as s:
            user = s.query(User).get(user_id)  
            if not user:
                raise HTTPException(status_code=404, detail="Account not found")
                
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

@app.get("/home/me")
def me(token:str =  Depends(verify_user)):
    nickname = token["username"],
    ids = token.get("sub")
    return{
        "nicname":nickname,
        "id":ids,
        
    }




UPLOAD_DIR = "/home/fedor-pomidor/my_proj/upload"  


os.makedirs(UPLOAD_DIR, exist_ok=True)  

@app.post("/home/recomendation/append", status_code=status.HTTP_201_CREATED)
async def create_post(
    file: UploadFile,
    tags: List[str] = Form(...),
    description: str = Form(...),
    token: str = Depends(verify_user)
):
    try:
        
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Можно загружать только изображения!"
            )

        
        file_extension = Path(file.filename).suffix if file.filename else ".jpg"
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        
        async with aiofiles.open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                await buffer.write(chunk)

        
        user_id = token["sub"]
        
        
        upload_record = WorkWithDB()
        resu = upload_record.set_photo(
            file_name=unique_filename,
            path=file_path,
            user_id=user_id,
            tags=tags,
            description=description
        )
        upload_record.insert_in_db()

        
        with session as s:
            user = s.query(User).get(user_id)
            if user:
                if user.posts_id:
                    user.posts_id += f",{unique_filename}"
                else:
                    user.posts_id = unique_filename
                s.commit()
            else:
                return JSONResponse(
                    status_code=404,
                    content={"error": "account not found"}
                )
        
        return {
            "status": "success",
            "filename": unique_filename,
            "path": file_path,
            "user_id": user_id,
            "tags": tags,
            "description": description
        }

    except Exception as e:
        
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке файла: {str(e)}"
        )
@app.get("/home/recomendation")
def get_recomendation(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Количество элементов на странице")
):
    try:
        db = WorkWithDB()
        
        
        skip = (page - 1) * limit
        
        
        photos = list(db.collection.find().skip(skip).limit(limit))
        
        
        total = db.collection.count_documents({})
        
       
        for photo in photos:
            photo["_id"] = str(photo["_id"])
            photo.pop("_sa_instance_state", None)
        
        
        return {
            "photos": photos,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit  
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении фото: {str(e)}"
        )
@app.post("/home/recomndation/set_favorite")
async def post_like(data: set_favorite, payload=Depends(verify_user)):
    db = DB()
    try:
        result = db.collection.find_one({"_id": data.id_post})
        

        sub = payload.get("sub")
        with session as s:
            user = s.query(User).get(sub)
            if not user:
                return {"error": "account not found"}

            
            if user.favorite_posts is None:
                user.favorite_posts = ""

            
            current_favorites = user.favorite_posts.split(",") if user.favorite_posts else []

            
            if str(data.id_post) in current_favorites:
                return {"error": "Пост уже в избранном"}

            
            updated_favorites = ",".join(current_favorites + [str(data.id_post)])
            user.favorite_posts = updated_favorites.strip(",")
            s.commit()

            return {"success": True, "message": "Пост добавлен в избранное"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
@app.get("/home/me/favorite-post")
def Get_Favorite(payload=Depends(verify_user)):
    try:
        sub = payload.get("sub")
        with session as s:
            user = s.query(User).get(sub)
            if not user:
                return {"error": "account not found"}
            
            db = WorkWithDB()
            my_favorite = user.favorite_posts.split(",")
            my_photos = []
            
            for i in my_favorite:
                i = i.strip()
                print(f"Searching for _id: '{i}'")
                
                try:
                    photo = db.collection.find_one({"_id": ObjectId(i)})
                    if photo:
                        
                        photo["_id"] = str(photo["_id"])  # ObjectId -> строка
                        if "data" in photo and isinstance(photo["data"], datetime):
                            photo["data"] = photo["data"].isoformat()  # datetime -> строка
                        my_photos.append(photo)
                except Exception as e:
                    print(f"Error processing photo {i}: {e}")
                    continue
            
            
            return jsonable_encoder(my_photos if my_photos else {"error": "No favorites found"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении фото: {str(e)}")
        
