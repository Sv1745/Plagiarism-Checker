from __future__ import annotations

import google.generativeai as genai


class Rewriter:
    def __init__(self, api_key: str, model_name: str):
        self.model_name = model_name
        self.enabled = bool(api_key)
        if self.enabled:
            genai.configure(api_key=api_key)

    def rewrite(self, text: str) -> str:
        if not self.enabled:
            return self._fallback(text)

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                (
                    'Rewrite the sentence to reduce semantic overlap while preserving exact meaning and academic tone. '
                    'Do not add new facts. Keep length similar. Return only rewritten sentence.\n\n'
                    f'Sentence: {text}'
                )
            )
            candidate = (response.text or '').strip()
            return candidate if candidate else self._fallback(text)
        except Exception:
            return self._fallback(text)

    @staticmethod
    def _fallback(text: str) -> str:
        words = text.split()
        if len(words) > 7:
            midpoint = len(words) // 2
            return ' '.join(words[midpoint:] + words[:midpoint])
        return text
