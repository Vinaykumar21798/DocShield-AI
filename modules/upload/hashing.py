import hashlib

DEFAULT_CHUNK_SIZE = 1024 * 1024


def compute_sha256(data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    sha = hashlib.sha256()
    view = memoryview(data)
    for offset in range(0, len(view), chunk_size):
        sha.update(view[offset : offset + chunk_size])
    return sha.hexdigest()


def stream_file_sha256(file_obj, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    sha = hashlib.sha256()
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        sha.update(chunk)
    return sha.hexdigest()
