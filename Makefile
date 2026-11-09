.PHONY: check seed db-setup validate validate-all legacy-all capture-golden setup reset

setup:
	python tools/provision_redshift.py
	python tools/source_connection.py all

reset:
	python tools/source_connection.py all

check:
	ruff check . && pytest && python tools/check_manifest.py

seed:
	python data/seed/generate_seed.py

db-setup:
	python tools/databricks_setup.py

validate:
	python -m validation.validate_unit --unit $(UNIT)

validate-all:
	@set -e; failed=""; \
	for u in $$(python -c "import yaml; m=yaml.safe_load(open('.migration/units.yaml')); \
	  print(' '.join(u for w in m['waves'] for u in w['units']))"); do \
	  if [ -f "$$(python -c "import yaml; m=yaml.safe_load(open('.migration/units.yaml')); \
	    print(m['units']['$$u']['target_dir'])")/etl.sql" ]; then \
	    echo "== validating $$u"; \
	    python -m validation.validate_unit --unit $$u || failed="$$failed $$u"; \
	  fi; \
	done; \
	if [ -n "$$failed" ]; then echo "FAILED:$$failed"; exit 1; fi; \
	echo "all validated units PASS"

legacy-all:
	python tools/source_connection.py all

capture-golden:
	python tools/source_connection.py capture
