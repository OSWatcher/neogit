import setuptools

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="neogit",
    version="0.0.1",
    author="Mathieu Tarral",
    author_email="mathieu.tarral@protonmail.com",
    description="Git implementation backed by Neo4j",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    package_data={"neogit": ["logging.yaml", "config/*.toml"]},
    install_requires=requirements,
    entry_points={
        "console_scripts": ["neogit = neogit.__main__:main"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
)
