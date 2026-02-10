from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserFetchOptions:
    headless: bool = True
    timeout_ms: int = 20_000
    wait_until: str = "networkidle"  # "load" | "domcontentloaded" | "networkidle"
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    slow_mo_ms: int = 300
    post_load_wait_ms: int = 1500


class BrowserHTMLFetcher:
    """Busca HTML usando um browser real (Playwright).

    Importante: o import do Playwright é lazy para não quebrar ambientes
    onde a dependência não está instalada/ativada.
    """

    def __init__(self, options: BrowserFetchOptions | None = None) -> None:
        self._options = options or BrowserFetchOptions()

    def fetch(self, url: str) -> str:
        """Navega até a URL e retorna o HTML renderizado."""

        try:
            # Lazy import: só exige Playwright quando esse fetcher é usado.
            from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Playwright não está disponível. Instale `playwright` e rode "
                "`playwright install chromium`."
            ) from exc

        def _looks_like_rj_block_page(html: str) -> bool:
            text = html.lower()
            return "secretaria de estado de fazenda do rio de janeiro".lower() in text

        def _fetch_once(playwright, headless: bool) -> str:
            launch_kwargs: dict = {
                "headless": headless,
                "slow_mo": self._options.slow_mo_ms,
            }
            browser = playwright.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                user_agent=self._options.user_agent,
                locale="pt-BR",
            )
            page = context.new_page()
            page.goto(
                url,
                wait_until=self._options.wait_until,
                timeout=self._options.timeout_ms,
            )
            # Aguarda um pouco após o carregamento para JS/redirects finais.
            page.wait_for_timeout(self._options.post_load_wait_ms)
            html = page.content()
            context.close()
            browser.close()
            return html

        with sync_playwright() as p:
            # 1ª tentativa: modo headless (silencioso)
            html = _fetch_once(p, headless=self._options.headless)

            # Se ainda parecer a página genérica da SEFAZ-RJ, tenta uma segunda
            # vez com browser visível (alguns bloqueios diferenciam headless).
            if _looks_like_rj_block_page(html) and self._options.headless:
                html = _fetch_once(p, headless=False)

        return html


__all__ = ["BrowserHTMLFetcher", "BrowserFetchOptions"]

