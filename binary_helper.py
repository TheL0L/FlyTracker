import pickle

def to_bytes(data) -> bytes:
    return pickle.dumps(data)

def from_bytes(binary_data : bytes):
    return pickle.loads(binary_data)

def hash_to_bytes(data) -> bytes:
    return data.encode(encoding='utf-8')

def hash_from_bytes(binary_data : bytes):
    return binary_data.decode(encoding='utf-8')

