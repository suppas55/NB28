from setuptools import setup

setup(
    name="nb28",
    version="0.1.1",
    packages=["NB28", "tests"],
    install_requires=[
        "chromadb",
        "fastapi",
        "uvicorn",
        "httpx",
        "requests",
    ],
    python_requires=">=3.8",
)
