from setuptools import setup, find_packages

from ms_certbot_nicru import __version__

setup(
    name="ms-certbot-nicru",
    version=__version__,
    description="NIC.RU DNS Authenticator plugin for Certbot",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/MrFrazers/ms-certbot-nicru",
    author="MrFras",
    author_email="mrfrazers@vk.com",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.25.0",
        "certbot>=2.0.0",
        "zope.interface",
    ],
    entry_points={
        "certbot.plugins": [
            "ms-dns-nicru = ms_certbot_nicru.authenticator:Authenticator",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
)
