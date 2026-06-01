"""M4STCLAW — Setup Configuration"""

from setuptools import setup, find_packages

setup(
    name="m4stclaw",
    version="3.4.0",
    description="Autonomous AI Mesh Network — Multi-provider LLM routing with MCP integration",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="M4ST",
    author_email="m4stanuj@users.noreply.github.com",
    url="https://github.com/m4stanuj/M4STCLAW",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "m4stclaw": ["ui/static/*"],
    },
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "httpx>=0.25.0",
        "pydantic>=2.5.0",
        "mcp>=0.1.0",
        "pillow>=10.0.0",
    ],
    extras_require={
        "full": [
            "chromadb>=0.5.0",
            "sentence-transformers>=2.2.2",
            "composio-core>=0.5.0",
            "playwright>=1.40.0",
            "pytesseract>=0.3.10",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "m4stclaw=m4stclaw.start:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
