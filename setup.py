import setuptools

import shrl

tests_require = [
    "flake8 >=3.4.1, <4.0",
    "hypothesis >=3.66.0, <4.0.0",
    "mypy >= 0.610",
]

install_requires = [
    "biopython >=1.14.0, <2.0",
    "pynucamino >=0.1.0, <1.0",
    "shared-schema >= 0.2",
    "SQLAlchemy >=1.1.14, <2.0",
    "tabulate >= 0.8",
]

setuptools.setup(
    name="shrl",
    version=shrl.__version__,
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": ["shrl = shrl.__main__:main"]},
    author="Nathaniel Knight",
    author_email="nknight@cfenet.ubc.ca",
    description=("The SHARED Quality, Uniformity, and Sanity Helper"),
    license="Apache2",
    url="https://github.com/hcv-shared/shrl",
    python_requires=">=3.6,<4",
    test_suite="tests",
    install_requires=install_requires,
    extras_require={"tests": tests_require},
)
