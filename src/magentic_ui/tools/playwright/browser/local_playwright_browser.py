from __future__ import annotations

from typing import Optional, Any, Dict
from pathlib import Path

from autogen_core import Component
from playwright.async_api import BrowserContext, Browser
from pydantic import BaseModel

from playwright.async_api import async_playwright, Playwright

from .base_playwright_browser import PlaywrightBrowser


class LocalPlaywrightBrowserConfig(BaseModel):
    """
    Configuration for the Local Playwright Browser.
    """

    headless: bool
    browser_channel: Optional[str] = None
    enable_downloads: bool = False
    persistent_context: bool = False
    browser_data_dir: Optional[str] = None

    @property
    def requires_persistent_context(self) -> bool:
        return self.persistent_context and self.browser_data_dir is not None


class LocalPlaywrightBrowser(
    PlaywrightBrowser, Component[LocalPlaywrightBrowserConfig]
):
    """
    A local Playwright browser implementation that provides flexible browser automation capabilities.
    Supports both persistent and non-persistent browser contexts, with configurable options for
    headless operation and download handling.

    Args:
        headless (bool): Whether to run the browser in headless mode.
        browser_channel (str, optional): The browser channel to use (e.g., 'chrome', 'msedge'). Default: None.
        enable_downloads (bool, optional): Whether to enable file downloads. Default: False.
        persistent_context (bool, optional): Whether to use a persistent browser context. Default: False.
        browser_data_dir (str, optional): Path to the browser user data directory for persistent contexts.
            Required if persistent_context is True. Default: None.

    Properties:
        browser_context (BrowserContext): The active Playwright browser context.
            Raises RuntimeError if accessed before browser is started.

    Example:
        ```python
        # Create a headful Chrome browser with persistent context
        browser = LocalPlaywrightBrowser(
            headless=False,
            browser_channel='chrome',
            persistent_context=True,
            browser_data_dir='./browser_data'
        )
        await browser.start()
        context = browser.browser_context
        # Use the browser for automation
        await browser.close()
        ```
    """

    component_config_schema = LocalPlaywrightBrowserConfig
    component_type = "other"

    def __init__(
        self,
        headless: bool = False,
        browser_channel: Optional[str] = None,
        enable_downloads: bool = False,
        persistent_context: bool = False,
        browser_data_dir: Optional[str] = None,
    ):
        super().__init__()
        self._headless = headless
        self._browser_channel = browser_channel
        self._enable_downloads = enable_downloads
        self._persistent_context = persistent_context
        self._browser_data_dir = browser_data_dir
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def _start(self) -> None:
            """
            Start the browser resource by connecting to local Chrome via CDP.
            """
            self._playwright = await async_playwright().start()
    
            print("DEBUG: Attempting to connect to existing Chrome instance on port 9222...")
            
            try:
                # Connect to the existing browser session
                self._browser = await self._playwright.chromium.connect_over_cdp("http://localhost:9222")
                
                # Use the existing default context if available (this holds your cookies/logins)
                if self._browser.contexts:
                    self._context = self._browser.contexts[0]
                else:
                    # If for some reason no context exists, create one, though CDP usually has one
                    self._context = await self._browser.new_context()
                    
                print("DEBUG: Successfully connected to local Chrome!")
                
            except Exception as e:
                print(f"ERROR: Could not connect to Chrome. Make sure it is running with --remote-debugging-port=9222. Error: {e}")
                raise e

    async def _close(self) -> None:
        """
        Close the connection, but DO NOT close the actual browser window.
        """
        # We pass on closing the context/browser so your actual Chrome window stays open
        # when you stop the agent.
        if self._playwright:
            await self._playwright.stop()

    @property
    def browser_context(self) -> BrowserContext:
        """
        Return the Playwright browser context.
        """
        if self._context is None:
            raise RuntimeError(
                "Browser context is not initialized. Start the browser first."
            )
        return self._context

    def _to_config(self) -> LocalPlaywrightBrowserConfig:
        """
        Convert the resource to its configuration.
        """
        return LocalPlaywrightBrowserConfig(
            headless=self._headless,
            browser_channel=self._browser_channel,
            enable_downloads=self._enable_downloads,
            persistent_context=self._persistent_context,
            browser_data_dir=self._browser_data_dir,
        )

    @classmethod
    def _from_config(
        cls, config: LocalPlaywrightBrowserConfig
    ) -> LocalPlaywrightBrowser:
        return cls(
            headless=config.headless,
            browser_channel=config.browser_channel,
            enable_downloads=config.enable_downloads,
            persistent_context=config.persistent_context,
            browser_data_dir=config.browser_data_dir,
        )
