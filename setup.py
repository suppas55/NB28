from setuptools import setup, find_packages

setup(
    name="nb28",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "chromadb",
        "fastapi",
        "uvicorn",
        "httpx",
        "requests",
    ],
    python_requires=">=3.8",
)