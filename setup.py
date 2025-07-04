"""
Setup configuration for the Distributed Edge AI Network.
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

# Read version
def get_version():
    """Get version from __init__.py"""
    with open(os.path.join("src", "__init__.py"), "r") as fh:
        for line in fh:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "0.1.0"

setup(
    name="distributed-edge-ai-network",
    version=get_version(),
    author="Edge AI Team",
    author_email="team@edgeai.example.com",
    description="A distributed edge AI network for smart city applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/distributed-edge-ai-network",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "pre-commit>=2.17.0",
        ],
        "web": [
            "flask>=2.0.0",
            "flask-cors>=3.0.0",
            "flask-socketio>=5.0.0",
            "eventlet>=0.33.0",
        ],
        "monitoring": [
            "prometheus-client>=0.13.0",
            "grafana-api>=1.0.0",
        ],
        "ml": [
            "tensorflow>=2.8.0",
            "torch>=1.11.0",
            "torchvision>=0.12.0",
            "scikit-learn>=1.0.0",
        ],
        "vision": [
            "opencv-python>=4.5.0",
            "pillow>=8.0.0",
        ],
        "audio": [
            "librosa>=0.8.0",
            "soundfile>=0.10.0",
        ],
        "all": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "pre-commit>=2.17.0",
            "flask>=2.0.0",
            "flask-cors>=3.0.0",
            "flask-socketio>=5.0.0",
            "eventlet>=0.33.0",
            "prometheus-client>=0.13.0",
            "grafana-api>=1.0.0",
            "tensorflow>=2.8.0",
            "torch>=1.11.0",
            "torchvision>=0.12.0",
            "scikit-learn>=1.0.0",
            "opencv-python>=4.5.0",
            "pillow>=8.0.0",
            "librosa>=0.8.0",
            "soundfile>=0.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "edge-coordinator=coordinator.main:main",
            "edge-node=edge_node.main:main",
            "edge-dashboard=web.dashboard.server:main",
        ],
    },
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt", "*.md"],
    },
    include_package_data=True,
    zip_safe=False,
    project_urls={
        "Bug Reports": "https://github.com/your-org/distributed-edge-ai-network/issues",
        "Source": "https://github.com/your-org/distributed-edge-ai-network",
        "Documentation": "https://distributed-edge-ai-network.readthedocs.io/",
    },
    keywords="edge computing, AI, machine learning, IoT, smart city, distributed systems",
)
