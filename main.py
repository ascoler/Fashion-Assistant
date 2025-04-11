from fastapi import FastAPI,UploadFile,HTTPException,Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel,EmailStr
from my_best_proj import analyze_image
import io
import bcrypt
from PIL import Image
import numpy as np
from database_structure import User,session
import auth
from mua import complementary_color
from my_best_proj import (
    load_clothing_model,
    remove_background,
    get_dominant_colors,
    classify_clothing,
)
from fastapi.middleware.cors import CORSMiddleware
import requests
from deep_translator import GoogleTranslator
app = FastAPI()
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
            
            existing_user = s.query(User).filter(User.name == data.name).one_or_none()
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
                "sub": new_user.id,  #
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
                "sub":result.id,
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
