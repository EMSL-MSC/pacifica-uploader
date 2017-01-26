#!/bin/bash -xe

coverage run --include='UploadServer/*' --include='home/*' -m home.uploader_unit_tests -v
coverage report -m
codeclimate-test-reporter
