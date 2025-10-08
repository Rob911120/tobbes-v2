"""
Tabs package for Tobbes v2 MainWindow.

Contains:
- ArticlesTab: Article management, verification, certificates
- ImportsTab: File import, processing, updates
"""

from .articles_tab import ArticlesTab
from .imports_tab import ImportsTab

__all__ = ["ArticlesTab", "ImportsTab"]
