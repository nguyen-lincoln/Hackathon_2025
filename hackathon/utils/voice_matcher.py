from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
from pathlib import Path
import os

encoder = VoiceEncoder()


def enroll_user(audio_path, user_id):
    wav = preprocess_wav(Path(audio_path))
    embedding = encoder.embed_utterance(wav)

    embeddings_dir = "utils/embeddings"
    os.makedirs(embeddings_dir, exist_ok=True)  # 🔥 ensures folder exists

    np.save(f"{embeddings_dir}/{user_id}.npy", embedding)
    return embedding

def identify_user(audio_path, threshold=0.75):
    wav = preprocess_wav(Path(audio_path))
    test_embedding = encoder.embed_utterance(wav)

    best_match = None
    best_score = -1

    for file in Path("utils/embeddings").glob("*.npy"):
        user_id = file.stem
        enrolled_embedding = np.load(file)
        similarity = np.inner(test_embedding, enrolled_embedding)

        if similarity > best_score:
            best_score = similarity
            best_match = user_id

    if best_score >= threshold:
        return best_match, best_score, True
    else:
        return None, best_score, False
