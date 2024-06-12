import hashlib

def compute_file_hash(file_path : str):
    """Compute SHA-256 hash of the given file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def verify_file_hash(file_path : str, assumed_hash : str) -> bool:
    """Verify the hash of the given file."""
    return compute_file_hash(file_path) == assumed_hash

