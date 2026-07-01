TCR=python .agents/skills/truecrime-cult-research/scripts/tcr.py

.PHONY: check init-sample validate-sample export-sample

check:
	python -m compileall src/case_builder .agents/skills/truecrime-cult-research/scripts
	$(TCR) validate data/examples/synthetic_case

init-sample:
	$(TCR) init-case data/cases/sample_case --title "Sample Case"

validate-sample:
	$(TCR) validate data/cases/sample_case

export-sample:
	$(TCR) export-manim data/cases/sample_case
	$(TCR) report data/cases/sample_case
