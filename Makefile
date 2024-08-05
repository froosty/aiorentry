lint:
	mypy aiorentry
	flake8 --show-source aiorentry
	isort --check-only aiorentry --diff

	flake8 --show-source tests
	isort --check-only tests --diff

test:
	pytest -s -v tests
