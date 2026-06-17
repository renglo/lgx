"""
LGX extension package
LangGraph conversational agents for the NOMA / Renglo platform
"""

from setuptools import setup, find_packages

setup(
    name="lgx-mod",
    version="1.0.0",
    description="LGX extension — LangGraph conversational agents on the Renglo platform",
    author="NOMA Team",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=[
        "langgraph>=0.2.0",
        "openai>=1.0.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
    ],
)
