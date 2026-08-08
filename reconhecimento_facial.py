import base64
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

import cv2
import numpy as np


def _decode_data_url_image(data_url):
    if not data_url or ',' not in data_url:
        raise ValueError('Imagem da câmera inválida.')

    _, encoded = data_url.split(',', 1)
    raw = base64.b64decode(encoded)
    nparr = np.frombuffer(raw, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Não foi possível decodificar a imagem capturada.')
    return frame


def _load_image(path):
    parsed = urlparse(str(path))
    if parsed.scheme in ('http', 'https'):
        with urlopen(str(path), timeout=10) as resp:
            raw = resp.read()
        nparr = np.frombuffer(raw, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('Foto de referência remota inválida.')
        return frame

    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError('Foto de referência não encontrada.')
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise ValueError('Foto de referência inválida.')
    return frame


def _extract_face(gray):
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

    if len(faces) == 0:
        return None

    # Mantém a maior face encontrada.
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return gray[y:y + h, x:x + w]


def _orb_signature(face_crop):
    resized = cv2.resize(face_crop, (220, 220))
    orb = cv2.ORB_create(nfeatures=800)
    keypoints, descriptors = orb.detectAndCompute(resized, None)
    return keypoints, descriptors


def comparar_rosto_por_orb(caminho_referencia, imagem_capturada_data_url, limiar=0.2):
    referencia_bgr = _load_image(caminho_referencia)
    captura_bgr = _decode_data_url_image(imagem_capturada_data_url)

    ref_gray = cv2.cvtColor(referencia_bgr, cv2.COLOR_BGR2GRAY)
    cap_gray = cv2.cvtColor(captura_bgr, cv2.COLOR_BGR2GRAY)

    face_ref = _extract_face(ref_gray)
    face_cap = _extract_face(cap_gray)

    if face_ref is None:
        return {
            'match': False,
            'score': 0.0,
            'mensagem': 'Nenhuma face detectada na foto de referência do aluno.'
        }

    if face_cap is None:
        return {
            'match': False,
            'score': 0.0,
            'mensagem': 'Nenhuma face detectada na captura da câmera. Tente novamente.'
        }

    kp_ref, desc_ref = _orb_signature(face_ref)
    kp_cap, desc_cap = _orb_signature(face_cap)

    if desc_ref is None or desc_cap is None or len(kp_ref) == 0 or len(kp_cap) == 0:
        return {
            'match': False,
            'score': 0.0,
            'mensagem': 'Não foi possível extrair pontos faciais suficientes para comparação.'
        }

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(desc_ref, desc_cap)

    if not matches:
        return {
            'match': False,
            'score': 0.0,
            'mensagem': 'Sem correspondência facial detectada.'
        }

    good_matches = [m for m in matches if m.distance < 50]
    base = max(len(kp_ref), len(kp_cap), 1)
    score = len(good_matches) / base
    match = score >= limiar

    return {
        'match': match,
        'score': round(score, 4),
        'mensagem': 'Correspondência facial sugerida.' if match else 'Rosto não confirmado pelo reconhecimento.'
    }
