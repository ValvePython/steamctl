define HELPBODY
Available commands:

	make help       - this thing.

	make init       - install python dependancies

	make dist		- build source distribution
	mage register	- register in pypi
	make upload 	- upload to pypi

endef

export HELPBODY
help:
	@echo "$$HELPBODY"

init:
	pip install -r requirements.txt

clean:
	rm -rf dist steamctl.egg-info build

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel

upload: dist
	twine upload -r pypi dist/*
