from setuptools import find_packages, setup

setup(
    name="gwaith",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pegasus-wms.api >= 5.1.1",
        "numpy",
        "scipy",
        "pyyaml",
        "matplotlib",
    ],
)
