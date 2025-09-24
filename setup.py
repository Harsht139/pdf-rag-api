from setuptools import setup, find_packages

setup(
    name="pdf-rag-api",
    version="0.1.0",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    install_requires=[
        # Dependencies will be installed from requirements.txt
    ],
    python_requires=">=3.8",
)
