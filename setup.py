from setuptools import setup

setup(
    name="nb28",
    version="0.1.0",
    packages=["tests"],
    install_requires=[
        "chromadb",
        "fastapi",
        "uvicorn",
        "httpx",
        "requests",
    ],
    python_requires=">=3.8",
)