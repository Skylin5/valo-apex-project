"""Utilitaire de recherche YouTube sans clé API."""

import re
import urllib.parse
import urllib.request

# ID de fallback si la recherche échoue
_FALLBACK_VIDEO_ID = "b1_6j039600"


def search_youtube(query: str) -> str:
    """Retourne l'ID YouTube du premier résultat pour *query*.

    Utilise un scraping léger de la page de résultats YouTube.
    En cas d'échec, retourne un ID de secours.
    """
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8")

        video_ids = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if video_ids:
            # Dédoublonnage tout en conservant l'ordre
            return list(dict.fromkeys(video_ids))[0]
    except Exception:
        pass

    return _FALLBACK_VIDEO_ID
