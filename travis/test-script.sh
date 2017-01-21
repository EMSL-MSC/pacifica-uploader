if [ "$RUN_LINTS" = "true" ] ; then
  pre-commit run --all-files
  bash -xe ./travis/static-analysis.sh
else
  bash -xe ./travis/unit-tests.sh
  bash -xe ./travis/test-deploy.sh
fi
