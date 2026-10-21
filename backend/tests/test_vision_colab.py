import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from src.compartido import vision_client


def _crear_imagen_prueba(ancho: int = 800, alto: int = 600) -> bytes:
    img = Image.new("RGB", (ancho, alto), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class VisionColabTests(unittest.TestCase):
    def setUp(self):
        self.test_host = "https://ejemplo-colab.ngrok-free.dev"

    def test_detecta_modelo_elegido_en_colab_mediante_alias(self):
        """Si Colab registró 'colab-activo', resuelve el modelo real que comparte su digest."""
        mock_tags_response = MagicMock()
        mock_tags_response.json.return_value = {
            "models": [
                {"name": "qwen2.5vl:3b", "digest": "sha256:aaa111", "modified_at": "2026-10-19T10:00:00Z"},
                {"name": "qwen2.5vl:7b", "digest": "sha256:bbb222", "modified_at": "2026-10-19T11:00:00Z"},
                {"name": "colab-activo:latest", "digest": "sha256:bbb222", "modified_at": "2026-10-19T11:01:00Z"},
            ]
        }
        with patch("src.compartido.vision_client.requests.get", return_value=mock_tags_response) as mock_get:
            modelo = vision_client.obtener_modelo_activo(self.test_host)

        self.assertEqual(modelo, "qwen2.5vl:7b")
        mock_get.assert_called_once_with(
            f"{self.test_host}/api/tags",
            headers=vision_client.OLLAMA_HEADERS,
            timeout=10,
        )

    def test_cambio_de_modelo_en_caliente_desde_colab(self):
        """Cambiar el modelo en Colab actualiza inmediatamente el modelo usado sin tocar .env."""
        resp_3b = MagicMock()
        resp_3b.json.return_value = {
            "models": [
                {"name": "qwen2.5vl:3b", "digest": "sha256:111"},
                {"name": "gemma3:12b", "digest": "sha256:222"},
                {"name": "colab-activo:latest", "digest": "sha256:111"},
            ]
        }
        resp_gemma = MagicMock()
        resp_gemma.json.return_value = {
            "models": [
                {"name": "qwen2.5vl:3b", "digest": "sha256:111"},
                {"name": "gemma3:12b", "digest": "sha256:222"},
                {"name": "colab-activo:latest", "digest": "sha256:222"},
            ]
        }
        with patch("src.compartido.vision_client.requests.get", side_effect=[resp_3b, resp_gemma]):
            primero = vision_client.obtener_modelo_activo(self.test_host)
            segundo = vision_client.obtener_modelo_activo(self.test_host)

        self.assertEqual(primero, "qwen2.5vl:3b")
        self.assertEqual(segundo, "gemma3:12b")

    def test_usa_modelo_mas_reciente_si_no_hay_alias_ni_fallback_en_servidor(self):
        """Si en Colab se descargó un modelo sin alias y no coincide con el local, usa el descargado en Colab."""
        mock_tags = MagicMock()
        mock_tags.json.return_value = {
            "models": [
                {"name": "llama3.2-vision:11b", "digest": "sha256:999", "modified_at": "2026-10-19T12:00:00Z"},
            ]
        }
        with patch.object(vision_client, "obtener_modelo_configurado", return_value="qwen2.5vl:3b"), \
             patch("src.compartido.vision_client.requests.get", return_value=mock_tags):
            modelo = vision_client.obtener_modelo_activo(self.test_host)

        self.assertEqual(modelo, "llama3.2-vision:11b")

    def test_recarga_dinamica_de_ollama_host_desde_env(self):
        """Si el usuario actualiza OLLAMA_HOST en .env con una nueva URL de Ngrok, se detecta sin reiniciar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("OLLAMA_HOST=https://nueva-sesion-colab.ngrok-free.dev/\n", encoding="utf-8")
            with patch.object(vision_client, "_ENV_FILE", env_path):
                host = vision_client.obtener_ollama_host()

        self.assertEqual(host, "https://nueva-sesion-colab.ngrok-free.dev")

    def test_pipeline_completo_dos_pasos_con_colab(self):
        """Verifica el flujo completo: detección de modelo en Colab -> bbox -> recorte -> extracción."""
        img_bytes = _crear_imagen_prueba()

        mock_tags = MagicMock()
        mock_tags.json.return_value = {
            "models": [
                {"name": "qwen2.5vl:7b", "digest": "sha256:777"},
                {"name": "colab-activo:latest", "digest": "sha256:777"},
            ]
        }

        mock_bbox_resp = MagicMock()
        mock_bbox_resp.json.return_value = {
            "message": {"content": json.dumps({"bbox_2d": [650, 550, 980, 980]})}
        }

        datos_extraidos = {
            "texto_extraido": "MUNICIPALIDAD DE LA PLATA - EXP 1940",
            "arquitecto": "Francisco Salamone",
            "anio": 1940,
            "titulo": "Corte Transversal",
            "ubicacion": "La Plata",
            "escala": "1:100",
            "tipo_de_plano": "corte",
            "material_soporte": "papel tela",
            "notas": "EXP 1940",
        }
        mock_extract_resp = MagicMock()
        mock_extract_resp.json.return_value = {
            "message": {"content": json.dumps(datos_extraidos)}
        }

        with patch.object(vision_client, "obtener_ollama_host", return_value=self.test_host), \
             patch("src.compartido.vision_client.requests.get", return_value=mock_tags) as mock_get, \
             patch("src.compartido.vision_client.requests.post", side_effect=[mock_bbox_resp, mock_extract_resp]) as mock_post:
            resultado = vision_client.extraer_datos_plano(img_bytes)

        self.assertEqual(resultado.arquitecto, "Francisco Salamone")
        self.assertEqual(resultado.anio, 1940)
        self.assertEqual(resultado.escala, "1:100")

        # Solo 1 llamada a /api/tags por plano y 2 llamadas a /api/chat (Paso 1 y Paso 2)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_post.call_count, 2)

        for call in mock_post.call_args_list:
            self.assertEqual(call.args[0], f"{self.test_host}/api/chat")
            self.assertEqual(call.kwargs["json"]["model"], "qwen2.5vl:7b")
            self.assertEqual(call.kwargs["headers"].get("ngrok-skip-browser-warning"), "true")

    def test_error_descriptivo_cuando_tunel_ngrok_esta_inactivo(self):
        """Si Ngrok devuelve 404 HTML por túnel caído, informa claramente que Colab está desconectado."""
        img_bytes = _crear_imagen_prueba()
        resp_ngrok_404 = MagicMock()
        resp_ngrok_404.status_code = 404
        resp_ngrok_404.text = "<!DOCTYPE html><html>ngrok ERR_NGROK_3200</html>"

        with patch.object(vision_client, "obtener_ollama_host", return_value=self.test_host), \
             patch("src.compartido.vision_client.requests.post", return_value=resp_ngrok_404):
            with self.assertRaises(vision_client.ExtraccionError) as ctx:
                vision_client.extraer_datos_cajetin(img_bytes, model="qwen2.5vl:7b")

        self.assertIn("túnel de Ngrok", str(ctx.exception))
        self.assertIn("Google Colab", str(ctx.exception))

    def test_conversion_bbox_en_pixeles_nativos_qwen(self):
        """Convierte correctamente bbox_2d en píxeles [xmin, ymin, xmax, ymax] de Qwen2.5-VL a [ymin, xmin, ymax, xmax] 0..1000."""
        img_bytes = _crear_imagen_prueba(1600, 1200)
        mock_bbox_resp = MagicMock()
        mock_bbox_resp.json.return_value = {
            "message": {"content": json.dumps({"bbox_2d": [939, 798, 1546, 1126]})}
        }
        with patch.object(vision_client, "obtener_ollama_host", return_value=self.test_host), \
             patch("src.compartido.vision_client.requests.post", return_value=mock_bbox_resp):
            bbox = vision_client.detectar_cajetin_bbox(img_bytes, model="qwen2.5vl:7b")

        # ymin=798/1200=665, xmin=939/1600=587, ymax=1126/1200=938, xmax=1546/1600=966
        self.assertEqual(bbox, [665, 587, 938, 966])


if __name__ == "__main__":
    unittest.main()

