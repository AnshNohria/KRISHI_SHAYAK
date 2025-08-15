import os
import traceback
print('Python:', os.sys.version)
try:
    import numpy as np
    print('NumPy:', np.__version__)
except Exception as e:
    print('NumPy import failed:', e)
    traceback.print_exc()
try:
    import chromadb
    from chromadb.config import Settings
    print('Chroma:', getattr(chromadb, '__version__', '?'))
    client = chromadb.PersistentClient(path='data/vector/chroma', settings=Settings(anonymized_telemetry=False))
    name = 'icar_advisory'
    try:
        col = client.get_collection(name)
        print('Got collection:', name)
    except Exception:
        col = client.create_collection(name, metadata={'hnsw:space': 'cosine'})
        print('Created collection:', name)
    print('Collection count:', len(col.get().get('ids', [])))
except Exception as e:
    print('Chroma import/use failed:', e)
    traceback.print_exc()
