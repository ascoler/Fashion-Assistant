import jwt
from datetime import datetime, timedelta

private_key_path = "/home/fedor-pomidor/my proj/secret/jwt-private.pem"
public_key_path = "/home/fedor-pomidor/my proj/secret/jwt-publick.pem"
algo = "RS256"
access_token_life: int = 259200

def encode_jwt(
    payload: dict,
    key_path: str = private_key_path,
    algo=algo,
    expire_timedelta: timedelta | None = None,
    expire_min: int = access_token_life
):
    
    with open(key_path, "r") as key_file:
        private_key = key_file.read()
    
    to_encode = payload.copy()
    now = datetime.utcnow()
    if expire_timedelta:
        exp = now + expire_timedelta
    else:
        exp = now + timedelta(minutes=expire_min)
    
    to_encode.update(
        exp=exp,
        iat=now
    )
    
    encoded = jwt.encode(to_encode, private_key, algorithm=algo)
    return encoded

def decode_jwt(token: str | bytes, algo=algo, public_key_path: str = public_key_path):
    try:
        with open(public_key_path, "r") as key_file:
            public_key = key_file.read()
        
        print(f"Public key: {public_key}")  
        print(f"Token to decode: {token}")  
        
        decoded = jwt.decode(token, public_key, algorithms=[algo])
        return decoded
    except Exception as e:
        print(f"Decode error: {str(e)}")  
        raise