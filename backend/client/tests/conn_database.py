import redis

r =  redis.Redis(decode_responses=True)

cursor = 0
while True:
    cursor, dados = r.hscan('Central',cursor=cursor) #type: ignore
    chaves = list(dados.keys())
    print(chaves)
    if cursor == 0:
        break