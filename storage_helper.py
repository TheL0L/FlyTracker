import hashing_helper as hasher
import file_helper as file_manager
import binary_helper

def generate_binary_filepath(video_path : str) -> str:
    return f'{file_manager.normalize_path(video_path)}_detection_storage.bin'

def write_binary_file(video_path : str, data) -> None:
    """Write SHA-256 hash and data to a binary file."""
    # generate a templated filepath for the storage file
    output_path = generate_binary_filepath(video_path)
    # compute video hash
    video_hash = hasher.compute_file_hash(video_path)

    with open(output_path, 'wb') as f:
        f.write(binary_helper.hash_to_bytes(video_hash))  # write the hash
        f.write(binary_helper.to_bytes(data))             # write the rest of the data

def read_binary_file(video_path : str) -> tuple[bool, dict]:
    """Read and verify the SHA-256 hash and data from a binary file."""
    # generate a templated filepath for the storage file
    output_path = generate_binary_filepath(video_path)

    with open(output_path, 'rb') as f:
        # read the hash
        file_hash = binary_helper.hash_from_bytes(f.read(64))

        # verify the storage file suits the provided video via the saved hash
        is_valid = hasher.verify_file_hash(video_path, file_hash)
        if not is_valid:
            return (False, None)
        
        # read the rest of the data
        data = binary_helper.from_bytes(f.read())
        return (True, data)

