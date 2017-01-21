#!/bin/bash -xe

coverage run --include='UploadServer/*' --include='home/*' -m home.uploader_unit_tests -v
codeclimate-test-reporter
