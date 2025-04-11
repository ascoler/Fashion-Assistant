import jwt
from datetime import datetime, timedelta

private_key_path = "/home/fedor-pomidor/my proj/secret/jwt-private.pem"
public_key_path = "/home/fedor-pomidor/my proj/secret/jwt-publick.pem"
algo = "RS256"
access_token_life: int = 30

def encode_jwt(
    payload: dict,
    key_path: str = private_key_path,
    algo=algo,
    expire_timedelta: timedelta | None = None,
    expire_min: int = access_token_life
):
    # Чтение приватного ключа из файла
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

def decode_jwt(
    token: str | bytes,
    algo=algo,
    public_key_path: str = public_key_path
):
    # Чтение публичного ключа из файла
    with open(public_key_path, "r") as key_file:
        public_key = key_file.read()
    
    decoded = jwt.decode(token, public_key, algorithms=[algo])
    return decoded