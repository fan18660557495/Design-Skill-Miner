from setuptools import find_packages, setup


setup(
    name="design-skill-miner",
    version="0.3.0",
    description="Turn repeated design conversations from local session exports into reusable skill drafts.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    entry_points={
        "console_scripts": [
            "design-skill-miner=design_skill_miner.cli:main",
        ]
    },
)
