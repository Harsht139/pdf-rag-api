from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name="pdf-rag-api",
    version="0.1.0",
    packages=find_packages(include=['app*']),
    package_dir={'': '.'},
    install_requires=required,
    python_requires=">=3.8",
    include_package_data=True,
)
